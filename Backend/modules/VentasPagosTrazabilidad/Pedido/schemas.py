from typing import Optional
from pydantic import BaseModel, model_validator
from datetime import datetime


class PedidoCreate(BaseModel):
    usuario_id: int
    direccion_id: Optional[int] = None
    forma_pago_codigo: str
    subtotal: float
    descuento: float = 0.00
    costo_envio: float = 50.00
    notas: Optional[str] = None

    @model_validator(mode="after")
    def validate_total(self):
        calculated_total = self.subtotal - self.descuento + self.costo_envio
        if calculated_total < 0:
            raise ValueError("El total no puede ser negativo")
        return self


class PedidoUpdate(BaseModel):
    direccion_id: Optional[int] = None
    forma_pago_codigo: Optional[str] = None
    notas: Optional[str] = None


class PedidoRead(BaseModel):
    id: int
    usuario_id: int
    direccion_id: Optional[int] = None
    estado_codigo: str
    forma_pago_codigo: str
    subtotal: float
    descuento: float
    costo_envio: float
    total: float
    notas: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
