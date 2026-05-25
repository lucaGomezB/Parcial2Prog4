from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class HistorialCreate(BaseModel):
    estado_hacia: str
    motivo: Optional[str] = None


class HistorialRead(BaseModel):
    id: int
    pedido_id: int
    estado_desde: Optional[str] = None
    estado_hacia: str
    usuario_id: Optional[int] = None
    motivo: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
