from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, Column
from decimal import Decimal
from sqlalchemy import ARRAY, Integer, Numeric
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
    precio_snapshot: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    subtotal_snap: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    personalizacion: Optional[List[int]] = Field(
        default=None, sa_column=Column(ARRAY(Integer))
    )

    # Only created_at - no updated_at (immutable row)
    created_at: datetime = Field(default_factory=get_utc_now, nullable=False)

    # Relationship
    pedido: "Pedido" = Relationship(back_populates="detalles")
