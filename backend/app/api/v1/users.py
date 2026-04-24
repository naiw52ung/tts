from pydantic import BaseModel
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.billing import UsageLedger
from app.models.user import User
from app.services.billing import DEFAULT_TASK_COST, admin_recharge

router = APIRouter()


class AdminRechargeRequest(BaseModel):
    email: str
    amount: int
    note: str = "manual_recharge"


@router.get("/me")
def me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ledgers = db.scalars(
        select(UsageLedger)
        .where(UsageLedger.user_id == current_user.id)
        .order_by(UsageLedger.id.desc())
        .limit(20)
    ).all()
    return {
        "id": current_user.id,
        "email": current_user.email,
        "phone": current_user.phone,
        "balance": current_user.balance,
        "task_cost": DEFAULT_TASK_COST,
        "recent_ledger": [
            {
                "id": item.id,
                "task_id": item.task_id,
                "amount": item.amount,
                "reason": item.reason,
                "created_at": item.created_at.isoformat(),
            }
            for item in ledgers
        ],
    }


@router.post("/admin/recharge")
def admin_user_recharge(
    payload: AdminRechargeRequest,
    x_admin_key: str = Header(default=""),
    db: Session = Depends(get_db),
) -> dict:
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY is not configured")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    target = db.scalar(select(User).where(User.email == payload.email))
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        admin_recharge(db, target, payload.amount, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(target)
    return {
        "email": target.email,
        "balance": target.balance,
        "amount": payload.amount,
        "note": payload.note,
    }
