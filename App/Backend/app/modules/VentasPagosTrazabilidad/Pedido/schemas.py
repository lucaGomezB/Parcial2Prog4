"""
Pedido schemas — Pydantic models for order API request/response.

Key concepts:
    - ItemPedidoRequest / PedidoCreate: what the frontend sends when creating an order
    - PedidoRead: what the API returns (includes nested details and user info)
    - Validation: total cannot be negative, stock validation schemas included
    - Snapshots: ItemPedidoRequest captures product name and price at order creation time
      so that later catalog changes don't affect historical records.
"""
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, model_validator, Field
from datetime import datetime
from app.core.base_schema import ReadModel


class ItemPedidoRequest(BaseModel):
    """Input schema for a single product line when creating an order.

    Uses price and name SNAPSHOTS — copies of the product's current values
    at order creation time. Future catalog changes won't affect this order.
    """
    producto_id: int
    cantidad: int = Field(gt=0)
    nombre_snapshot: str
    precio_snapshot: Decimal
    personalizacion: Optional[List[int]] = None


class PedidoCreate(BaseModel):
    """Request schema for creating a new order (POST /pedidos).

    usuario_id is optional: if omitted, the router forces it to the
    authenticated user's ID (prevents order forgery).

    The model_validator total check ensures:
        subtotal - descuento + costo_envio >= 0
    Negative totals are rejected.
    """
    usuario_id: Optional[int] = None
    direccion_id: Optional[int] = None
    forma_pago_codigo: str
    subtotal: Decimal
    descuento: Decimal = Decimal('0.00')
    costo_envio: Decimal = Decimal('0.00')
    notas: Optional[str] = None
    detalles: Optional[List[ItemPedidoRequest]] = None

    @model_validator(mode="after")
    def validate_total(self):
        """Business rule: order total must never be negative."""
        calculated_total = self.subtotal - self.descuento + self.costo_envio
        if calculated_total < 0:
            raise ValueError("El total no puede ser negativo")
        return self


class PedidoUpdate(BaseModel):
    """Request schema for updating an order (PATCH).

    All fields optional — only provided fields are applied (exclude_unset).
    Does NOT allow changing state or totals — those have dedicated endpoints.
    """
    direccion_id: Optional[int] = None
    forma_pago_codigo: Optional[str] = None
    notas: Optional[str] = None
    detalles: Optional[List[ItemPedidoRequest]] = None


class DetallePedidoRead(ReadModel):
    """Response schema for a single detail line within an order."""
    producto_id: int
    cantidad: int
    nombre_snapshot: str
    precio_snapshot: Decimal
    subtotal_snap: Decimal
    personalizacion: Optional[List[int]] = None


class UsuarioInfo(ReadModel):
    """Minimal user info embedded in PedidoRead — no sensitive data exposed."""
    id: int
    nombre: str
    apellido: str
    email: str


class PedidoRead(ReadModel):
    """Response schema for a single order, including nested details and user info."""
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
    direccion_snapshot: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    detalles: Optional[List[DetallePedidoRead]] = None
    usuario: Optional[UsuarioInfo] = None


class PedidoAvanzarResponse(BaseModel):
    """Response schema for the state advance endpoint.

    Returns both the previous and current state for confirmation.
    """
    id: int
    estado_anterior: str
    estado_actual: str
    mensaje: str


class PedidoCancelarResponse(BaseModel):
    """Response schema for the cancel endpoint.

    Always ends in CANCELADO state.
    """
    id: int
    estado_anterior: str
    estado_actual: str
    mensaje: str


class StockInsuficienteDetalle(BaseModel):
    """Details of a single item with insufficient stock."""
    producto_id: int
    nombre_producto: str
    cantidad_solicitada: int
    stock_disponible: int


class StockInsuficienteError(BaseModel):
    """Structured error response when stock validation fails."""
    error: str = "stock_insuficiente"
    mensaje: str
    detalles: List[StockInsuficienteDetalle]


class DetallePedidoUpdate(BaseModel):
    """Schema for modifying a detail line's quantity.

    cantidad = 0 means the detail line should be removed.
    """
    cantidad: int = Field(ge=0)  # 0 = remove the detail


class ValidarStockDetalleInput(BaseModel):
    """Input: product + quantity pair for stock validation."""
    producto_id: int
    cantidad: int = Field(gt=0)


class ValidarStockInput(BaseModel):
    """Input: list of products to validate stock for."""
    detalles: list[ValidarStockDetalleInput]


class ValidarStockDetalleResponse(BaseModel):
    """Output: stock availability for a single product."""
    producto_id: int
    nombre_producto: str
    cantidad_solicitada: int
    stock_disponible: int


class StockItemResponse(BaseModel):
    """Stock information for a single product — always returned regardless of validation result."""
    producto_id: int
    nombre_producto: str
    stock_disponible: int


class ValidarStockIngredienteResponse(BaseModel):
    """Output: shortage for a single shared ingredient (aggregated across products)."""
    ingrediente_id: int
    ingrediente_nombre: str
    cantidad_solicitada: int
    stock_disponible: int
    unidad_medida_simbolo: Optional[str] = None


class ValidarStockResponse(BaseModel):
    """Output: overall stock validation result with details of shortfalls
    and stock info for ALL products (always populated)."""
    valido: bool
    detalles: list[ValidarStockDetalleResponse] = []
    ingredientes: list[ValidarStockIngredienteResponse] = []
    items: list[StockItemResponse] = []


class DisponibilidadInput(BaseModel):
    """Input: current cart items + the product IDs to check availability for."""
    carrito: list[ValidarStockDetalleInput] = []
    productos: list[int] = []


class ProductoLimitante(BaseModel):
    """A cart product that consumes a shared ingredient constraining another product."""
    producto_id: int
    nombre: str


class ProductoDisponibilidad(BaseModel):
    """Output: how many more units of a product can still be added given the cart.
    `limitantes` lists the OTHER cart products that consume the ingredient(s)
    currently constraining this product (so the UI can tell the client what to reduce)."""
    producto_id: int
    agregable: int
    limitantes: list[ProductoLimitante] = []


class DisponibilidadResponse(BaseModel):
    """Output: addable quantities for the requested products (0 = not addable now)."""
    productos: list[ProductoDisponibilidad] = []


class CancelarPedidoInput(BaseModel):
    """Request schema for cancelling an order with a required motivo.

    motivo must be a non-empty string between 1 and 500 characters.
    """
    motivo: str = Field(..., min_length=1, max_length=500)

