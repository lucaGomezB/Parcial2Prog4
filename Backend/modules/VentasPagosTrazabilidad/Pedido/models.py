from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
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
    subtotal: float = Field(nullable=False)
    descuento: float = Field(default=0.00, nullable=False)
    costo_envio: float = Field(default=50.00, nullable=False)
    total: float = Field(nullable=False)
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
