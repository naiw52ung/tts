from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.billing import UsageLedger
from app.models.user import User

DEFAULT_TASK_COST = 10
TRIAL_BALANCE = 100


def charge_task_cost(db: Session, user: User, task_id: int = None) -> None:
    if user.balance < DEFAULT_TASK_COST:
        raise ValueError("Insufficient balance")
    user.balance -= DEFAULT_TASK_COST
    db.add(user)
    db.add(
        UsageLedger(
            user_id=user.id,
            task_id=task_id,
            amount=-DEFAULT_TASK_COST,
            reason="task_submit",
        )
    )


def admin_recharge(db: Session, user: User, amount: int, note: str = "manual_recharge") -> None:
    if amount <= 0:
        raise ValueError("amount must be positive")
    user.balance += amount
    db.add(user)
    db.add(
        UsageLedger(
            user_id=user.id,
            task_id=None,
            amount=amount,
            reason=note,
        )
    )
