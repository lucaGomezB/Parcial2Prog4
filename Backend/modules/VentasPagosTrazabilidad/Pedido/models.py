from typing import Optional, List, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import Numeric
from sqlmodel import SQLModel, Field, Relationship, Column
from models.base import TimestampModel, SoftDeleteModel

# Same-package imports — safe, no circular dependency
from ..EstadoPedido.models import EstadoPedido
from ..FormaPago.models import FormaPago
from ..DetallePedido.models import DetallePedido
from ..HistorialEstadoPedido.models import HistorialEstadoPedido
from ..Pago.models import Pago

# Cross-module references — stay under TYPE_CHECKING to avoid circular imports
if TYPE_CHECKING:
    from modules.IdentidadYAcceso.Usuario.models import Usuario
    from modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega


class PedidoBase(TimestampModel):
    usuario_id: int = Field(foreign_key="usuario.id", nullable=False)
    direccion_id: Optional[int] = Field(default=None, foreign_key="direcciones_entrega.id", ondelete="SET NULL")
    estado_codigo: str = Field(foreign_key="estadopedido.codigo", nullable=False)
    forma_pago_codigo: str = Field(foreign_key="formapago.codigo", nullable=False)
    subtotal: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    descuento: Decimal = Field(default=Decimal('0.00'), sa_column=Column(Numeric(precision=10, scale=2)))
    costo_envio: Decimal = Field(default=Decimal('50.00'), sa_column=Column(Numeric(precision=10, scale=2)))
    total: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    notas: Optional[str] = Field(default=None)


class Pedido(PedidoBase, SoftDeleteModel, table=True):
    __tablename__ = "pedido"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Relationships — cross-module references kept as strings (lazy resolution)
    usuario: "Usuario" = Relationship(back_populates="pedidos")
    direccion: Optional["DireccionEntrega"] = Relationship()

    # Relationships — same-package (eager-safe because directly imported)
    estado: "EstadoPedido" = Relationship()
    forma_pago: "FormaPago" = Relationship()
    detalles: List["DetallePedido"] = Relationship(back_populates="pedido", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    historial_estados: List["HistorialEstadoPedido"] = Relationship(back_populates="pedido", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    pagos: List["Pago"] = Relationship(back_populates="pedido")
