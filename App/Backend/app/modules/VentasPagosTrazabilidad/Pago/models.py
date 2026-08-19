"""
Pago models — Payment entity for order payment tracking.

Each payment is linked to an order and stores MercadoPago integration fields:
    - mp_payment_id: MercadoPago's internal payment ID
    - mp_status: payment status from MP (approved, pending, rejected, etc.)
    - mp_status_detail: detailed status description from MP
    - external_reference: unique reference sent to MP (links back to this record)
    - idempotency_key: ensures webhook processing is idempotent (no double-charge)
    - transaction_amount: the amount charged
    - payment_method_id: the specific MP payment method used (credit card, etc.)
"""
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column
from sqlalchemy import Numeric
from app.core.base import TimestampModel

if TYPE_CHECKING:
    from ..Pedido.models import Pedido


class Pago(TimestampModel, table=True):
    """Payment record linked to an order. Maps to 'pago' table.

    Includes MercadoPago integration fields for payment lifecycle tracking.
    The idempotency_key ensures webhook events aren't processed twice.
    """

    __tablename__ = "pago"

    id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: Optional[int] = Field(default=None, foreign_key="pedido.id", nullable=True)
    mp_payment_id: Optional[int] = Field(default=None, unique=True)
    mp_status: str = Field(max_length=30, nullable=False)
    mp_status_detail: Optional[str] = Field(default=None, max_length=100)
    external_reference: str = Field(unique=True, max_length=100, nullable=False)
    idempotency_key: str = Field(unique=True, max_length=100, nullable=False)
    transaction_amount: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    payment_method_id: Optional[str] = Field(default=None, max_length=50)

    # Relationship back to parent order
    pedido: "Pedido" = Relationship(back_populates="pagos")
