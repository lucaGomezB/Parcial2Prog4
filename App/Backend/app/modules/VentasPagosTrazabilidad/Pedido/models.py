"""
Pedido models — Order entity, the central table of the Sales module.

Each order has:
    - A customer (usuario)
    - A delivery address (direccion)
    - A current state (estado_codigo) following a Finite State Machine
    - A payment method (forma_pago)
    - Multiple detail lines (DetallePedido) — the purchased products
    - An append-only state history (HistorialEstadoPedido)

Orders are NEVER physically deleted — SoftDeleteModel adds deleted_at.
The state machine transitions are hardcoded in PedidoService.
"""
from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import JSON, Column, Numeric
from sqlmodel import SQLModel, Field, Relationship
from app.core.base import TimestampModel, SoftDeleteModel

# Same-package imports — safe, no circular dependency
from ..EstadoPedido.models import EstadoPedido
from ..FormaPago.models import FormaPago
from ..DetallePedido.models import DetallePedido
from ..HistorialEstadoPedido.models import HistorialEstadoPedido
from ..Pago.models import Pago

# Cross-module references — stay under TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from app.modules.IdentidadYAcceso.Usuario.models import Usuario
    from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega


class PedidoBase(TimestampModel):
    """Base mix-in with all order columns except PK and relationships.

    Inherits TimestampModel (created_at, updated_at).

    Key fields:
        usuario_id: who owns the order (FK -> usuario)
        direccion_id: delivery address (FK -> direcciones_entrega)
        estado_codigo: current order state as a semantic string key
        forma_pago_codigo: selected payment method
        subtotal: sum of product prices before discount
        descuento: discount amount (promotion, coupon, etc.)
        costo_envio: shipping cost (0 if pickup, default $50)
        total: subtotal - descuento + costo_envio (never negative)
    """
    usuario_id: int = Field(foreign_key="usuario.id", nullable=False)
    direccion_id: Optional[int] = Field(default=None, foreign_key="direcciones_entrega.id", ondelete="SET NULL")
    estado_codigo: str = Field(foreign_key="estadopedido.codigo", nullable=False)
    forma_pago_codigo: str = Field(foreign_key="formapago.codigo", nullable=False)
    subtotal: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    descuento: Decimal = Field(default=Decimal('0.00'), sa_column=Column(Numeric(precision=10, scale=2)))
    costo_envio: Decimal = Field(default=Decimal('50.00'), sa_column=Column(Numeric(precision=10, scale=2)))
    total: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    notas: Optional[str] = Field(default=None)
    direccion_snapshot: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class Pedido(PedidoBase, SoftDeleteModel, table=True):
    """Order table (pedido) — the central entity of the Sales module.

    SoftDeleteModel adds deleted_at for logical deletion.
    Relationships use cascade="all, delete-orphan" for details and history,
    meaning when an order is deleted (even logically), its children disappear.

    Relationships:
        - usuario: the customer who placed the order
        - direccion: delivery address
        - estado: the current EstadoPedido object (joined via estado_codigo)
        - forma_pago: the selected payment method
        - detalles: list of DetallePedido (products with price snapshots)
        - historial_estados: append-only log of all state changes
        - pagos: payments associated with this order
    """
    __tablename__ = "pedido"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relationships — cross-module references use string-based lazy resolution
    usuario: "Usuario" = Relationship(back_populates="pedidos")
    direccion: Optional["DireccionEntrega"] = Relationship()

    # Relationships — same-package (eager-safe because directly imported)
    estado: "EstadoPedido" = Relationship()
    forma_pago: "FormaPago" = Relationship()
    detalles: List["DetallePedido"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    historial_estados: List["HistorialEstadoPedido"] = Relationship(
        back_populates="pedido",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    pagos: List["Pago"] = Relationship(back_populates="pedido")
