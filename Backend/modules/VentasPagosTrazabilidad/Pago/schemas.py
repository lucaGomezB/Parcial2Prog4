"""
Pago schemas — Pydantic models for payment API.

PagoCreate is used when initializing a payment (sending to MercadoPago).
PagoUpdate is used when receiving webhook updates from MP.
PagoRead is the response schema with all payment details.
"""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class PagoCreate(BaseModel):
    """Request schema for creating a payment record.

    Used when initializing a payment to be sent to MercadoPago.
    The idempotency_key prevents duplicate charges on retry.
    """
    pedido_id: int
    mp_status: str = "pending"
    external_reference: str
    idempotency_key: str
    transaction_amount: float
    payment_method_id: Optional[str] = None


class PagoUpdate(BaseModel):
    """Request schema for updating a payment status.

    Used when receiving MercadoPago webhook callbacks to update
    the payment's status (approved, rejected, etc.).
    """
    mp_status: Optional[str] = None
    mp_status_detail: Optional[str] = None
    mp_payment_id: Optional[int] = None


class PagoRead(BaseModel):
    """Response schema for a payment record."""
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
