from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.payment import PaymentOrder
from app.models.user import User
from app.schemas.payment import PaymentCreateRequest, PaymentOrderResponse
from app.services.billing import admin_recharge

router = APIRouter()


@router.post("/orders", response_model=PaymentOrderResponse)
def create_payment_order(
    payload: PaymentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentOrderResponse:
    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="amount must be positive")
    order = PaymentOrder(
        user_id=current_user.id,
        order_no=f"PO{uuid4().hex[:20].upper()}",
        amount=payload.amount,
        channel=payload.channel,
        status="pending",
        remark=payload.remark,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return PaymentOrderResponse.model_validate(order)


@router.get("/orders", response_model=list[PaymentOrderResponse])
def list_payment_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PaymentOrderResponse]:
    orders = db.scalars(
        select(PaymentOrder)
        .where(PaymentOrder.user_id == current_user.id)
        .order_by(PaymentOrder.id.desc())
    ).all()
    return [PaymentOrderResponse.model_validate(item) for item in orders]


@router.post("/orders/{order_no}/mock-paid")
def mark_order_paid(
    order_no: str,
    x_admin_key: str = Header(default=""),
    db: Session = Depends(get_db),
) -> dict:
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="ADMIN_API_KEY is not configured")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin key")

    order = db.scalar(select(PaymentOrder).where(PaymentOrder.order_no == order_no))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "paid":
        return {"order_no": order.order_no, "status": order.status, "balance_changed": False}

    user = db.get(User, order.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Order user not found")

    admin_recharge(db, user, order.amount, note=f"payment:{order.order_no}")
    order.status = "paid"
    order.paid_at = datetime.utcnow()
    db.add(order)
    db.commit()
    return {
        "order_no": order.order_no,
        "status": order.status,
        "amount": order.amount,
        "user_id": order.user_id,
        "balance_changed": True,
    }
