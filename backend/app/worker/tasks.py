from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import patoolib
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.task import ModifyInstruction, Task
from app.services.legend_modifier import apply_drop_rate_changes
from app.services.llm_parser import parse_drop_requirement
from app.worker.celery_app import celery_app


def append_log(db: Session, task: Task, line: str, progress: Optional[int] = None) -> None:
    task.log_text = (task.log_text or "") + line + "\n"
    if progress is not None:
        task.progress = progress
    db.add(task)
    db.commit()


def extract_archive(source: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower()
    if suffix == ".zip":
        shutil.unpack_archive(str(source), str(target_dir))
        return
    patoolib.extract_archive(str(source), outdir=str(target_dir), verbosity=-1)


@celery_app.task(name="process_legend_task")
def process_legend_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if not task:
            return
        task.status = "processing"
        append_log(db, task, "任务开始处理", 5)

        task_root = Path(task.original_path).parent
        unpack_dir = task_root / "unpacked"
        output_zip = task_root / "output.zip"

        append_log(db, task, "正在解压上传包", 15)
        extract_archive(Path(task.original_path), unpack_dir)

        append_log(db, task, "正在解析需求", 30)
        instruction = parse_drop_requirement(task.req_doc_text)

        append_log(db, task, "正在执行爆率修改", 60)
        modified = apply_drop_rate_changes(unpack_dir, instruction)
        for item in modified:
            db.add(
                ModifyInstruction(
                    task_id=task.id,
                    type="爆率",
                    target_file=item["target_file"],
                    operation=item["operation"],
                    old_content=item["old_content"],
                    new_content=item["new_content"],
                    status="done",
                )
            )
        db.commit()

        append_log(db, task, f"修改完成，共 {len(modified)} 处变更", 80)
        append_log(db, task, "正在打包输出", 90)
        shutil.make_archive(str(output_zip.with_suffix("")), "zip", str(unpack_dir))

        task.output_path = str(output_zip)
        task.status = "success"
        append_log(db, task, "任务完成", 100)
    except Exception as exc:
        task = db.get(Task, task_id)
        if task:
            task.status = "failed"
            task.error_msg = str(exc)
            append_log(db, task, f"任务失败: {exc}", task.progress or 0)
    finally:
        db.close()
