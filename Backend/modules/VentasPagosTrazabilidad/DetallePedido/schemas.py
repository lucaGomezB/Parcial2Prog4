from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime


class DetallePedidoCreate(BaseModel):
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    personalizacion: Optional[List[int]] = None


class DetallePedidoRead(BaseModel):
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
