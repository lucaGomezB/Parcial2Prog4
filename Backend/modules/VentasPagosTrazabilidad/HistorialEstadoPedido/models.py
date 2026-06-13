"""
HistorialEstadoPedido models — Append-only order state history (audit log).

This is an APPEND-ONLY table: rows are INSERTed, never UPDATEd or DELETEd.
Every state change in the order lifecycle creates one row.

Why APPEND-ONLY?
    To maintain a COMPLETE TRACEABILITY for each order:
        - When was it created? (estado_desde = NULL)
        - When was it confirmed? (PENDIENTE -> CONFIRMADO)
        - Who confirmed it? (usuario_id)
        - When was it cancelled? (X -> CANCELADO)
        - Why was it cancelled? (motivo)

Typical trace for an order:
    created_at   | desde        | hacia        | user | motivo
    -------------+--------------+--------------+------+--------
    10:00        | NULL         | PENDIENTE    | 1    |
    10:01        | PENDIENTE    | CONFIRMADO   | 1    |
    10:30        | CONFIRMADO   | EN_PREP      | 2    |
    10:45        | EN_PREP      | EN_CAMINO    | 2    |
    11:00        | EN_CAMINO    | ENTREGADO    | 2    |
"""
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone

if TYPE_CHECKING:
    from ..Pedido.models import Pedido


def get_utc_now():
    return datetime.now(timezone.utc)


class HistorialEstadoPedido(SQLModel, table=True):
    """Append-only audit log for order state transitions (historialestadopedido)."""

    __tablename__ = "historialestadopedido"

    id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedido.id", nullable=False, ondelete="CASCADE")
    estado_desde: Optional[str] = Field(default=None, foreign_key="estadopedido.codigo", ondelete="SET NULL")
    estado_hacia: str = Field(foreign_key="estadopedido.codigo", nullable=False)
    usuario_id: Optional[int] = Field(default=None, foreign_key="usuario.id", ondelete="SET NULL")
    motivo: Optional[str] = Field(default=None)
    es_sistema: bool = Field(default=False)

    # Only created_at — no updated_at (append-only, never modified)
    created_at: datetime = Field(default_factory=get_utc_now, nullable=False)

    # Relationship back to parent order
    pedido: "Pedido" = Relationship(back_populates="historial_estados")
