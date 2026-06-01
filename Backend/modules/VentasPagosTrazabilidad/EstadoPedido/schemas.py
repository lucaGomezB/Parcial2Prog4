"""
EstadoPedido schemas — Pydantic models for order status API.
"""
from typing import Optional
from pydantic import BaseModel


class EstadoPedidoCreate(BaseModel):
    """Request schema for creating a new order status."""
    codigo: str
    descripcion: str
    orden: int
    es_terminal: bool = False


class EstadoPedidoUpdate(BaseModel):
    """Request schema for updating an order status. All fields optional."""
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    es_terminal: Optional[bool] = None


class EstadoPedidoRead(BaseModel):
    """Response schema for an order status."""
    codigo: str
    descripcion: str
    orden: int
    es_terminal: bool

    class Config:
        from_attributes = True
