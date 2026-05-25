from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from models.base import TimestampModel

if TYPE_CHECKING:
    from ..Pedido.models import Pedido


class Pago(TimestampModel, table=True):
    __tablename__ = "pago"

    id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedido.id", nullable=False)
    mp_payment_id: Optional[int] = Field(default=None, unique=True)
    mp_status: str = Field(max_length=30, nullable=False)
    mp_status_detail: Optional[str] = Field(default=None, max_length=100)
    external_reference: str = Field(unique=True, max_length=100, nullable=False)
    idempotency_key: str = Field(unique=True, max_length=100, nullable=False)
    transaction_amount: float = Field(nullable=False)
    payment_method_id: Optional[str] = Field(default=None, max_length=50)

    # Relationship
    pedido: "Pedido" = Relationship(back_populates="pagos")
