"""
DetallePedido schemas — Pydantic models for order detail API.

These schemas are used by the Pedido service for creating detail lines
and by the API for returning detail data embedded in PedidoRead responses.
"""
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class DetallePedidoCreate(BaseModel):
    """Request schema for creating an individual detail line.

    Note: pedido_id is NOT included here — it comes from the URL path.
    """
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    personalizacion: Optional[List[int]] = None


class DetallePedidoRead(BaseModel):
    """Response schema for a detail line, nested inside PedidoRead.

    Includes subtotal_snap (precio_snapshot * cantidad) computed by the service.
    """
    pedido_id: int
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    subtotal_snap: Decimal
    personalizacion: Optional[List[int]] = None
    created_at: datetime

    class Config:
        from_attributes = True
