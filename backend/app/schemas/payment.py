from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PaymentCreateRequest(BaseModel):
    amount: int
    channel: str = "mock"
    remark: Optional[str] = None


class PaymentOrderResponse(BaseModel):
    order_no: str
    amount: int
    channel: str
    status: str
    remark: Optional[str]
    created_at: datetime
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True
