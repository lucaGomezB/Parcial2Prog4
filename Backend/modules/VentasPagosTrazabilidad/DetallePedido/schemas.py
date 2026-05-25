from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class DetallePedidoCreate(BaseModel):
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: float
    personalizacion: Optional[str] = None  # JSON array string like "[1,2,3]"


class DetallePedidoRead(BaseModel):
    pedido_id: int
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: float
    subtotal_snap: float
    personalizacion: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
