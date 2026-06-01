"""
DetallePedido models — Order detail line entity (a product within an order).

COMPOSITE PRIMARY KEY: (pedido_id, producto_id)
    This prevents duplicate product entries within the same order.
    If the customer wants more quantity, the 'cantidad' field is incremented.

SNAPSHOTS:
    nombre_snapshot and precio_snapshot are COPIES of the product's name and
    price at order creation time. This ensures historical accuracy — if the
    product's price changes later, existing orders retain their original values.

IMMUTABLE:
    Only has created_at (no updated_at). Detail rows are never modified
    after creation (except cantidad changes on PENDIENTE orders).
"""
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
    """Order detail line. Maps to 'detallepedido' table.

    Each row represents one product purchased in an order.
    Uses composite PK (pedido_id + producto_id) — no duplicate products per order.
    """
    __tablename__ = "detallepedido"

    # Composite primary key
    pedido_id: int = Field(
        foreign_key="pedido.id", primary_key=True,
        ondelete="CASCADE", nullable=False
    )
    producto_id: int = Field(
        foreign_key="producto.id", primary_key=True,
        ondelete="RESTRICT", nullable=False
    )
    cantidad: int = Field(nullable=False)  # SMALLINT in DB

    # Snapshots — copies of product data at order creation time
    nombre_snapshot: str = Field(max_length=200, nullable=False)
    precio_snapshot: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    subtotal_snap: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    personalizacion: Optional[List[int]] = Field(
        default=None, sa_column=Column(ARRAY(Integer))
    )

    # Only created_at — no updated_at (immutable row)
    created_at: datetime = Field(default_factory=get_utc_now, nullable=False)

    # Relationship back to parent order
    pedido: "Pedido" = Relationship(back_populates="detalles")
