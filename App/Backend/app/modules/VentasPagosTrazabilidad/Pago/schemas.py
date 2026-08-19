"""
Pago schemas — Pydantic models for payment API.

PagoCreate is used when initializing a payment (sending to MercadoPago).
PagoUpdate is used when receiving webhook updates from MP.
PagoRead is the response schema with all payment details.
InitFromCartRequest is the new schema for the post-pago flow.
"""
from typing import Optional, List, Literal
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from app.core.base_schema import ReadModel


class PagoCreate(BaseModel):
    """Request schema for creating a payment record.

    Used when initializing a payment to be sent to MercadoPago.
    The idempotency_key prevents duplicate charges on retry.
    pedido_id is optional for the new init-from-cart flow.
    """
    pedido_id: Optional[int] = None
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


class PagoRead(ReadModel):
    """Response schema for a payment record."""
    id: int
    pedido_id: Optional[int] = None
    mp_payment_id: Optional[int] = None
    mp_status: str
    mp_status_detail: Optional[str] = None
    external_reference: str
    idempotency_key: str
    transaction_amount: float
    payment_method_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class InitPaymentRequest(BaseModel):
    """Request schema for initiating a MercadoPago payment (legacy, deprecated)."""
    pedido_id: int


class InitPaymentResponse(BaseModel):
    """Response schema after initiating a MercadoPago payment."""
    pago: PagoRead
    init_point: Optional[str] = None
    error: Optional[str] = None


class CartItemInput(BaseModel):
    """A single cart item in the init-from-cart request."""
    producto_id: int
    nombre: str
    precio: Decimal
    cantidad: int
    ingredientes_excluidos: Optional[List[int]] = None


class InitFromCartRequest(BaseModel):
    """Request schema: POST /pagos/init-from-cart — initiate MP payment from cart.

    The frontend sends the cart contents directly instead of a pedido_id.
    Stock is validated, a Pago is created (pedido_id=NULL), a cart_snapshot
    is created, and a MercadoPago preference is returned.
    """
    forma_pago_codigo: str
    subtotal: Decimal
    descuento: Decimal = Decimal("0.00")
    costo_envio: Decimal = Decimal("0.00")
    direccion_id: Optional[int] = None
    notas: Optional[str] = None
    items: List[CartItemInput]


class PaymentStatusResponse(BaseModel):
    """Response schema for GET /pagos/status polling endpoint."""
    status: Literal["found", "pending", "not_found", "error"]
    pedido_id: Optional[int] = None
    mp_status: Optional[str] = None
    error: Optional[str] = None
