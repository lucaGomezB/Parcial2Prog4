from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, model_validator
from datetime import datetime


class DetallePedidoInput(BaseModel):
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    personalizacion: Optional[List[int]] = None
    medida_id: Optional[int] = None


class PedidoCreate(BaseModel):
    usuario_id: Optional[int] = None
    direccion_id: Optional[int] = None
    forma_pago_codigo: str
    subtotal: Decimal
    descuento: Decimal = Decimal('0.00')
    costo_envio: Decimal = Decimal('50.00')
    notas: Optional[str] = None
    detalles: Optional[List[DetallePedidoInput]] = None

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


class DetallePedidoRead(BaseModel):
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    subtotal_snap: Decimal
    personalizacion: Optional[List[int]] = None
    medida_snapshot: Optional[str] = None

    class Config:
        from_attributes = True


class UsuarioInfo(BaseModel):
    id: int
    nombre: str
    apellido: str
    email: str

    class Config:
        from_attributes = True


class PedidoRead(BaseModel):
    id: int
    usuario_id: int
    direccion_id: Optional[int] = None
    estado_codigo: str
    forma_pago_codigo: str
    subtotal: Decimal
    descuento: Decimal
    costo_envio: Decimal
    total: Decimal
    notas: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    detalles: Optional[List[DetallePedidoRead]] = None
    usuario: Optional[UsuarioInfo] = None

    class Config:
        from_attributes = True


class PedidoAvanzarResponse(BaseModel):
    id: int
    estado_anterior: str
    estado_actual: str
    mensaje: str


class PedidoCancelarResponse(BaseModel):
    id: int
    estado_anterior: str
    estado_actual: str
    mensaje: str


class StockInsuficienteDetalle(BaseModel):
    producto_id: int
    nombre_producto: str
    medida: Optional[str] = None
    cantidad_solicitada: int
    stock_disponible: int


class StockInsuficienteError(BaseModel):
    error: str = "stock_insuficiente"
    mensaje: str
    detalles: List[StockInsuficienteDetalle]


class DetallePedidoUpdate(BaseModel):
    cantidad: int  # 0 = eliminar el detalle
