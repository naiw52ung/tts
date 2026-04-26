from __future__ import annotations

import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.learning import LearningSample
from app.models.task import ModifyInstruction, Task


def upsert_learning_sample(db: Session, task: Task) -> None:
    existing = db.scalar(select(LearningSample).where(LearningSample.task_id == task.id))
    changes = db.scalars(select(ModifyInstruction).where(ModifyInstruction.task_id == task.id)).all()
    payload = [
        {
            "type": item.type,
            "target_file": item.target_file,
            "operation": item.operation,
            "old_content": item.old_content,
            "new_content": item.new_content,
            "status": item.status,
        }
        for item in changes
    ]
    if existing:
        existing.raw_requirement = task.req_doc_text
        existing.result_status = task.status
        existing.error_msg = task.error_msg
        existing.applied_changes = json.dumps(payload, ensure_ascii=False)
        db.add(existing)
        return
    db.add(
        LearningSample(
            task_id=task.id,
            user_id=task.user_id,
            raw_requirement=task.req_doc_text,
            result_status=task.status,
            error_msg=task.error_msg,
            applied_changes=json.dumps(payload, ensure_ascii=False),
        )
    )
