from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone

if TYPE_CHECKING:
    from ..Pedido.models import Pedido


def get_utc_now():
    return datetime.now(timezone.utc)


class HistorialEstadoPedido(SQLModel, table=True):
    __tablename__ = "historialestadopedido"

    id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedido.id", nullable=False, ondelete="CASCADE")
    estado_desde: Optional[str] = Field(default=None, foreign_key="estadopedido.codigo", ondelete="SET NULL")
    estado_hacia: str = Field(foreign_key="estadopedido.codigo", nullable=False)
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuario.id", ondelete="SET NULL")
    motivo: Optional[str] = Field(default=None)

    # Only created_at - no updated_at (append-only)
    created_at: datetime = Field(default_factory=get_utc_now, nullable=False)

    # Relationship
    pedido: "Pedido" = Relationship(back_populates="historial_estados")
