"""
EstadoPedido schemas — Pydantic models for order status API response.
"""
from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class EstadoPedidoRead(BaseModel):
    """Response schema for a single order status."""
    codigo: str
    descripcion: str
    orden: int
    es_terminal: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
