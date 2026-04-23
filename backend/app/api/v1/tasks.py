import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskResponse
from app.services.storage import save_upload
from app.worker.tasks import process_legend_task

router = APIRouter()

SUPPORTED_EXT = {".zip", ".rar", ".7z"}
ENGINE_MAP = {"GOM": 1, "GEE": 2}


@router.post("", response_model=TaskResponse)
async def create_task(
    engine: str = Form(...),
    version_type: str = Form(...),
    req_doc_text: str = Form(...),
    version_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    ext = Path(version_file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise HTTPException(status_code=400, detail="Only ZIP/RAR/7z supported")
    if engine not in ENGINE_MAP:
        raise HTTPException(status_code=400, detail="Only GOM/GEE supported in prototype")

    task = Task(
        user_id=current_user.id,
        engine_id=ENGINE_MAP[engine],
        version_type=version_type,
        original_filename=version_file.filename or "unknown",
        original_path="",
        req_doc_text=req_doc_text,
        status="pending",
        progress=0,
        log_text="任务已创建\n",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    saved_path = await save_upload(task.id, version_file)
    task.original_path = saved_path
    db.add(task)
    db.commit()
    db.refresh(task)

    process_legend_task.delay(task.id)
    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == int(user_id)))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("")
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TaskResponse]:
    tasks = db.scalars(select(Task).where(Task.user_id == current_user.id).order_by(Task.id.desc())).all()
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/{task_id}/download")
def download_task_output(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    if not task or task.status != "success" or not task.output_path:
        raise HTTPException(status_code=404, detail="Output not ready")
    return FileResponse(task.output_path, filename=f"task_{task_id}_output.zip")


@router.get("/{task_id}/logs")
async def stream_task_logs(
    task_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        sent = ""
        while True:
            current = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == int(user_id)))
            if not current:
                yield "event: end\ndata: {}\n\n"
                return
            log_text = current.log_text or ""
            delta = log_text[len(sent) :]
            if delta:
                payload = {"status": current.status, "progress": current.progress, "delta": delta}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                sent = log_text
            if current.status in {"success", "failed"}:
                yield "event: end\ndata: {}\n\n"
                return
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
