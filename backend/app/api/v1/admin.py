from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.billing import UsageLedger
from app.models.learning import LearningSample, TaskFeedback
from app.models.payment import PaymentOrder
from app.models.task import Task
from app.models.user import User
from app.models.template_candidate import TemplateCandidate
from app.services.template_candidates import approve_template_candidate, rebuild_template_candidates, reject_template_candidate

router = APIRouter()


def _validate_admin_key(x_admin_key: str = Header(default="")) -> str:
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY is not configured")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return x_admin_key


def require_admin(x_admin_key: str = Header(default="")) -> None:
    _validate_admin_key(x_admin_key)


def normalize_error_reason(error_msg: str) -> str:
    message = (error_msg or "").strip()
    if not message:
        return "unknown"
    if ":" in message:
        return message.split(":", 1)[0].strip()[:80]
    return message[:80]


@router.get("/overview")
def admin_overview(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    total_users = db.scalar(select(func.count(User.id))) or 0
    total_tasks = db.scalar(select(func.count(Task.id))) or 0
    pending_tasks = db.scalar(select(func.count(Task.id)).where(Task.status.in_(["pending", "processing", "cancelling"]))) or 0
    failed_tasks = db.scalar(select(func.count(Task.id)).where(Task.status == "failed")) or 0
    paid_orders = db.scalar(select(func.count(PaymentOrder.id)).where(PaymentOrder.status == "paid")) or 0
    total_recharge = db.scalar(select(func.coalesce(func.sum(UsageLedger.amount), 0)).where(UsageLedger.amount > 0)) or 0
    return {
        "total_users": int(total_users),
        "total_tasks": int(total_tasks),
        "pending_tasks": int(pending_tasks),
        "failed_tasks": int(failed_tasks),
        "paid_orders": int(paid_orders),
        "total_recharge": int(total_recharge),
        "total_feedback": int(db.scalar(select(func.count(TaskFeedback.id))) or 0),
        "total_learning_samples": int(db.scalar(select(func.count(LearningSample.id))) or 0),
        "total_template_candidates": int(db.scalar(select(func.count(TemplateCandidate.id))) or 0),
    }


@router.get("/users")
def admin_users(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict]:
    users = db.scalars(select(User).order_by(User.id.desc()).limit(limit)).all()
    return [
        {
            "id": item.id,
            "email": item.email,
            "phone": item.phone,
            "balance": item.balance,
            "created_at": item.created_at.isoformat(),
        }
        for item in users
    ]


@router.get("/tasks")
def admin_tasks(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[dict]:
    stmt = select(Task).order_by(Task.id.desc()).limit(limit)
    if status:
        stmt = select(Task).where(Task.status == status).order_by(Task.id.desc()).limit(limit)
    tasks = db.scalars(stmt).all()
    return [
        {
            "id": item.id,
            "user_id": item.user_id,
            "status": item.status,
            "progress": item.progress,
            "req_doc_text": item.req_doc_text,
            "error_msg": item.error_msg,
            "created_at": item.created_at.isoformat(),
        }
        for item in tasks
    ]


@router.get("/orders")
def admin_orders(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[dict]:
    stmt = select(PaymentOrder).order_by(PaymentOrder.id.desc()).limit(limit)
    if status:
        stmt = select(PaymentOrder).where(PaymentOrder.status == status).order_by(PaymentOrder.id.desc()).limit(limit)
    orders = db.scalars(stmt).all()
    users = {item.id: item.email for item in db.scalars(select(User)).all()}
    return [
        {
            "order_no": item.order_no,
            "user_id": item.user_id,
            "user_email": users.get(item.user_id, ""),
            "amount": item.amount,
            "channel": item.channel,
            "status": item.status,
            "remark": item.remark,
            "created_at": item.created_at.isoformat(),
            "paid_at": item.paid_at.isoformat() if item.paid_at else None,
        }
        for item in orders
    ]


@router.get("/failures-summary")
def admin_failures_summary(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=200, ge=20, le=1000),
) -> dict:
    failed_tasks = db.scalars(
        select(Task)
        .where(Task.status == "failed")
        .order_by(Task.id.desc())
        .limit(limit)
    ).all()

    grouped: dict[str, int] = {}
    samples: list[dict] = []
    for item in failed_tasks:
        reason = normalize_error_reason(item.error_msg or "")
        grouped[reason] = grouped.get(reason, 0) + 1
        if len(samples) < 20:
            samples.append(
                {
                    "task_id": item.id,
                    "user_id": item.user_id,
                    "error_msg": item.error_msg,
                    "created_at": item.created_at.isoformat(),
                }
            )

    top_reasons = sorted(grouped.items(), key=lambda x: x[1], reverse=True)
    return {
        "total_failed_sampled": len(failed_tasks),
        "top_reasons": [{"reason": key, "count": value} for key, value in top_reasons[:20]],
        "recent_failed_samples": samples,
    }


@router.get("/feedbacks")
def admin_feedbacks(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[dict]:
    rows = db.scalars(select(TaskFeedback).order_by(TaskFeedback.id.desc()).limit(limit)).all()
    return [
        {
            "id": item.id,
            "task_id": item.task_id,
            "user_id": item.user_id,
            "rating": item.rating,
            "comment": item.comment,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
        for item in rows
    ]


@router.get("/learning-samples")
def admin_learning_samples(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[dict]:
    rows = db.scalars(select(LearningSample).order_by(LearningSample.id.desc()).limit(limit)).all()
    return [
        {
            "id": item.id,
            "task_id": item.task_id,
            "user_id": item.user_id,
            "result_status": item.result_status,
            "raw_requirement": item.raw_requirement,
            "error_msg": item.error_msg,
            "created_at": item.created_at.isoformat(),
        }
        for item in rows
    ]


@router.get("/template-candidates")
def admin_template_candidates(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
) -> list[dict]:
    stmt = select(TemplateCandidate).order_by(TemplateCandidate.id.desc()).limit(limit)
    if status:
        stmt = select(TemplateCandidate).where(TemplateCandidate.status == status).order_by(TemplateCandidate.id.desc()).limit(limit)
    rows = db.scalars(stmt).all()
    return [
        {
            "id": item.id,
            "name": item.name,
            "category": item.category,
            "description": item.description,
            "default_requirement": item.default_requirement,
            "source_count": item.source_count,
            "status": item.status,
            "review_note": item.review_note,
            "created_at": item.created_at.isoformat(),
            "approved_at": item.approved_at.isoformat() if item.approved_at else None,
        }
        for item in rows
    ]


@router.post("/template-candidates/rebuild")
def admin_rebuild_template_candidates(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    min_count: int = Query(default=2, ge=1, le=20),
) -> dict:
    inserted = rebuild_template_candidates(db, min_count=min_count)
    return {"inserted": inserted, "min_count": min_count}


@router.post("/template-candidates/{candidate_id}/approve")
def admin_approve_template_candidate(
    candidate_id: int,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    candidate = db.get(TemplateCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Template candidate not found")
    if candidate.status == "approved":
        return {"candidate_id": candidate_id, "status": "approved", "template_created": False}
    template = approve_template_candidate(db, candidate)
    return {
        "candidate_id": candidate_id,
        "status": "approved",
        "template_created": True,
        "template_id": template.id,
        "template_name": template.name,
    }


@router.post("/template-candidates/{candidate_id}/reject")
def admin_reject_template_candidate(
    candidate_id: int,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
    note: str = Query(default="manual_review_rejected"),
) -> dict:
    candidate = db.get(TemplateCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Template candidate not found")
    if candidate.status == "approved":
        raise HTTPException(status_code=400, detail="Approved candidate cannot be rejected")
    reject_template_candidate(db, candidate, note=note)
    return {"candidate_id": candidate_id, "status": "rejected", "note": note}
