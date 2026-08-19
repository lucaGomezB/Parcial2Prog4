"""
CarritoSnapshot model — persists cart state during the async payment window.

The snapshot is created at payment initiation (init_from_cart) and consumed
(deleted) atomically inside the same UoW that creates the Pedido on payment
confirmation. If the payment is abandoned, the snapshot expires after 30 min.
"""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.modules.IdentidadYAcceso.Usuario.models import Usuario
    from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega


def _utc_now():
    return datetime.now(timezone.utc)


def _default_expires_at():
    return _utc_now() + timedelta(minutes=30)


class CarritoSnapshot(SQLModel, table=True):
    """Cart snapshot held during MercadoPago payment window.

    TTL is 30 minutes from creation. Expired snapshots are cleaned up
    by a background task every 5 minutes.
    """

    __tablename__ = "carrito_snapshot"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        max_length=36,
    )
    usuario_id: int = Field(foreign_key="usuario.id", nullable=False)
    items: list[dict] = Field(sa_column=Column(JSONB, nullable=False))
    direccion_id: Optional[int] = Field(
        default=None,
        foreign_key="direcciones_entrega.id",
        ondelete="SET NULL",
    )
    direccion_snapshot: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    forma_pago_codigo: str = Field(max_length=30, nullable=False)
    costo_envio: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    subtotal: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    total: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    external_reference: str = Field(max_length=100, nullable=False, unique=True)
    notas: Optional[str] = Field(default=None)
    expires_at: datetime = Field(default_factory=_default_expires_at, nullable=False)
    created_at: datetime = Field(default_factory=_utc_now, nullable=False)

    # Relationships
    usuario: "Usuario" = Relationship()
    direccion: Optional["DireccionEntrega"] = Relationship()
