"""
HistorialEstadoPedido schemas — Pydantic models for order state history API.

The history is APPEND-ONLY: only creation is exposed. HistorialCreate
is minimal because pedido_id, estado_desde, and usuario_id are set
automatically by the service/unit-of-work layer.
"""
from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class HistorialCreate(BaseModel):
    """Request schema for creating a history entry.

    Note: pedido_id and estado_desde are NOT here — they are set
    automatically by the UoW avanzar_estado() method.
    """
    estado_hacia: str
    motivo: Optional[str] = None


class HistorialRead(BaseModel):
    """Response schema for a single history entry.

    Shows the complete transition: from state -> to state, who did it,
    why, and when.
    """
    id: int
    pedido_id: int
    estado_desde: Optional[str] = None
    estado_hacia: str
    usuario_id: Optional[int] = None
    motivo: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
