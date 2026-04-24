from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.task import Task
from app.models.template import PromptTemplate
from app.models.user import User
from app.schemas.task import DryRunResponse, TaskResponse, TemplateResponse
from app.services.billing import DEFAULT_TASK_COST, charge_task_cost
from app.services.legend_modifier import apply_drop_rate_changes
from app.services.llm_parser import parse_drop_requirement
from app.services.storage import save_upload
from app.worker.tasks import extract_archive
from app.worker.tasks import process_legend_task

router = APIRouter()

SUPPORTED_EXT = {".zip", ".rar", ".7z"}
ENGINE_MAP = {"GOM": 1, "GEE": 2}


def _resolve_requirement(db: Session, template_id: Optional[int], req_doc_text: Optional[str]) -> str:
    if req_doc_text and req_doc_text.strip():
        return req_doc_text.strip()
    if template_id is None:
        raise HTTPException(status_code=400, detail="Please provide req_doc_text or template_id")
    template = db.get(PromptTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template.default_requirement


@router.get("/templates", response_model=list[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TemplateResponse]:
    templates = db.scalars(select(PromptTemplate).order_by(PromptTemplate.id.asc())).all()
    return [TemplateResponse.model_validate(item) for item in templates]


@router.post("/dry-run", response_model=DryRunResponse)
async def dry_run_task(
    engine: str = Form(...),
    version_type: str = Form(...),
    req_doc_text: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    version_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DryRunResponse:
    del version_type
    del current_user
    ext = Path(version_file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise HTTPException(status_code=400, detail="Only ZIP/RAR/7z supported")
    if engine not in ENGINE_MAP:
        raise HTTPException(status_code=400, detail="Only GOM/GEE supported in prototype")

    final_requirement = _resolve_requirement(db, template_id, req_doc_text)
    instruction = parse_drop_requirement(final_requirement)

    with tempfile.TemporaryDirectory(prefix="legendai-dryrun-") as tmp:
        archive_path = Path(tmp) / (version_file.filename or "input.zip")
        archive_path.write_bytes(await version_file.read())
        unpack_dir = Path(tmp) / "unpacked"
        extract_archive(archive_path, unpack_dir)
        changes = apply_drop_rate_changes(unpack_dir, instruction)

    return DryRunResponse(
        instruction={
            "target_keyword": instruction.target_keyword,
            "change_percent": instruction.change_percent,
        },
        change_count=len(changes),
        changes=changes[:200],
    )


@router.post("", response_model=TaskResponse)
async def create_task(
    engine: str = Form(...),
    version_type: str = Form(...),
    req_doc_text: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    version_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    ext = Path(version_file.filename or "").suffix.lower()
    if ext not in SUPPORTED_EXT:
        raise HTTPException(status_code=400, detail="Only ZIP/RAR/7z supported")
    if engine not in ENGINE_MAP:
        raise HTTPException(status_code=400, detail="Only GOM/GEE supported in prototype")
    if current_user.balance < DEFAULT_TASK_COST:
        raise HTTPException(status_code=402, detail="Insufficient balance")
    final_requirement = _resolve_requirement(db, template_id, req_doc_text)

    task = Task(
        user_id=current_user.id,
        engine_id=ENGINE_MAP[engine],
        version_type=version_type,
        original_filename=version_file.filename or "unknown",
        original_path="",
        req_doc_text=final_requirement,
        status="pending",
        progress=0,
        log_text="任务已创建\n",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    charge_task_cost(db, current_user, task.id)
    db.commit()

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
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/cancel", response_model=TaskResponse)
def cancel_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in {"success", "failed"}:
        raise HTTPException(status_code=400, detail="Completed task cannot be cancelled")
    if task.status == "cancelled":
        return task
    if task.status == "pending":
        task.status = "cancelled"
        task.progress = task.progress or 0
        task.log_text = (task.log_text or "") + "任务已取消\n"
    else:
        task.status = "cancelling"
        task.log_text = (task.log_text or "") + "收到取消请求，任务将尽快停止\n"
    db.add(task)
    db.commit()
    db.refresh(task)
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
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == int(user_id)))
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
            if current.status in {"success", "failed", "cancelled"}:
                yield "event: end\ndata: {}\n\n"
                return
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
