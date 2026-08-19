"""
HistorialStock schemas — Pydantic models for stock audit API.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.core.base_schema import ReadModel


class HistorialStockCreate(BaseModel):
    """Request schema for creating a HistorialStock entry."""
    entidad_tipo: str
    entidad_id: int
    stock_anterior: int
    stock_nuevo: int
    motivo: str
    usuario_id: Optional[int] = None


class HistorialStockRead(ReadModel):
    """Response schema for a HistorialStock entry."""
    id: int
    entidad_tipo: str
    entidad_id: int
    stock_anterior: int
    stock_nuevo: int
    motivo: str
    usuario_id: Optional[int] = None
    created_at: datetime
