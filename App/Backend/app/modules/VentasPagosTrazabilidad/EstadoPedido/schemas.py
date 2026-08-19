"""
EstadoPedido schemas — Pydantic models for order status API response.
"""
from typing import Optional
from datetime import datetime
from app.core.base_schema import ReadModel


class EstadoPedidoRead(ReadModel):
    """Response schema for a single order status."""
    codigo: str
    descripcion: str
    orden: int
    es_terminal: bool
    created_at: datetime
    updated_at: datetime
