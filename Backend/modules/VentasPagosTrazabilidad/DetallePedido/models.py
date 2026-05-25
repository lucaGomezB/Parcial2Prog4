from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone

if TYPE_CHECKING:
    from ..Pedido.models import Pedido


def get_utc_now():
    return datetime.now(timezone.utc)


class DetallePedido(SQLModel, table=True):
    __tablename__ = "detallepedido"

    pedido_id: int = Field(
        foreign_key="pedido.id", primary_key=True,
        ondelete="CASCADE", nullable=False
    )
    producto_id: int = Field(
        foreign_key="producto.id", primary_key=True,
        ondelete="RESTRICT", nullable=False
    )
    cantidad: int = Field(nullable=False)  # SMALLINT in DB
    nombre_snapshot: str = Field(max_length=200, nullable=False)
    precio_snapshot: float = Field(nullable=False)
    subtotal_snap: float = Field(nullable=False)
    personalizacion: Optional[str] = Field(default=None)  # JSON string representing INTEGER[]

    # Only created_at - no updated_at (immutable row)
    created_at: datetime = Field(default_factory=get_utc_now, nullable=False)

    # Relationship
    pedido: "Pedido" = Relationship(back_populates="detalles")
