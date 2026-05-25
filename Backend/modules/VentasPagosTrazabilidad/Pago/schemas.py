from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class PagoCreate(BaseModel):
    pedido_id: int
    mp_status: str = "pending"
    external_reference: str
    idempotency_key: str
    transaction_amount: float
    payment_method_id: Optional[str] = None


class PagoUpdate(BaseModel):
    mp_status: Optional[str] = None
    mp_status_detail: Optional[str] = None
    mp_payment_id: Optional[int] = None


class PagoRead(BaseModel):
    id: int
    pedido_id: int
    mp_payment_id: Optional[int] = None
    mp_status: str
    mp_status_detail: Optional[str] = None
    external_reference: str
    idempotency_key: str
    transaction_amount: float
    payment_method_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
