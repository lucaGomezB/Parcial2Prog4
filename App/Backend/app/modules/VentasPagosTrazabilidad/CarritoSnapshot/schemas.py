"""
CarritoSnapshot schemas — Pydantic models for cart snapshot API.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel
from app.core.base_schema import ReadModel


class CartItemSchema(BaseModel):
    """A single cart item within a snapshot."""
    producto_id: int
    nombre: str
    precio: Decimal
    cantidad: int
    ingredientes_excluidos: Optional[List[int]] = None


class CarritoSnapshotCreate(BaseModel):
    """Input for creating a cart snapshot."""
    usuario_id: int
    external_reference: str
    forma_pago_codigo: str
    subtotal: Decimal
    costo_envio: Decimal
    total: Decimal
    items: List[CartItemSchema]
    direccion_id: Optional[int] = None
    direccion_snapshot: Optional[dict] = None
    notas: Optional[str] = None


class CarritoSnapshotRead(ReadModel):
    """Response schema for a cart snapshot."""
    id: str
    usuario_id: int
    items: List[dict]
    direccion_id: Optional[int] = None
    direccion_snapshot: Optional[dict] = None
    forma_pago_codigo: str
    costo_envio: Decimal
    subtotal: Decimal
    total: Decimal
    external_reference: str
    notas: Optional[str] = None
    expires_at: datetime
    created_at: datetime
