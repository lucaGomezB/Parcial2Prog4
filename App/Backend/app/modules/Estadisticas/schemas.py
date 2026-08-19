"""
Estadisticas schemas — Pydantic response models for the analytics dashboard.

All monetary fields use Decimal(10,2) — NEVER Python float.
fecha fields are str (DATE_TRUNC returns a string representation).
"""
from decimal import Decimal
from app.core.base_schema import ReadModel


class ResumenResponse(ReadModel):
    """KPI summary response: four key performance indicators."""
    ventas_hoy: Decimal
    ticket_promedio: Decimal
    pedidos_activos: int
    mes_actual: Decimal


class VentasPeriodoItem(ReadModel):
    """Single data point in the sales-over-time chart."""
    fecha: str
    total: Decimal


class ProductoTopItem(ReadModel):
    """A product in the top-selling ranking."""
    producto_id: int
    nombre: str
    cantidad_vendida: int
    ingresos: Decimal


class PedidosEstadoItem(ReadModel):
    """Count of orders grouped by status code."""
    estado_codigo: str
    cantidad: int


class IngresosResponse(ReadModel):
    """Revenue grouped by payment method."""
    forma_pago_codigo: str
    total: Decimal
