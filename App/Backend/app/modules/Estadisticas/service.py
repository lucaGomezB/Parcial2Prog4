"""
Estadisticas service — KPI calculation and response assembly.

Each static method receives a session, instantiates the repository,
calls the appropriate repo method, and returns Pydantic response models.

Edge cases handled:
- Zero-data scenarios return Decimal('0.00') and 0, never None.
- Empty result sets for chart endpoints return empty lists.
"""
from decimal import Decimal
from datetime import date
from sqlmodel import Session

from .uow import EstadisticasUnitOfWork
from .schemas import (
    ResumenResponse,
    VentasPeriodoItem,
    ProductoTopItem,
    PedidosEstadoItem,
    IngresosResponse,
)


class EstadisticasService:
    """Orchestrates analytics queries and assembles response objects."""

    @staticmethod
    def get_resumen(session: Session) -> ResumenResponse:
        """Return the four KPI indicators for the dashboard summary."""
        with EstadisticasUnitOfWork(session) as uow:
            kpis = uow.estadisticas.get_resumen_kpis()

            return ResumenResponse(
                ventas_hoy=Decimal(kpis["ventas_hoy"] or 0),
                ticket_promedio=Decimal(kpis["ticket_promedio"] or 0),
                pedidos_activos=int(kpis["pedidos_activos"] or 0),
                mes_actual=Decimal(kpis["mes_actual"] or 0),
            )

    @staticmethod
    def get_ventas_periodo(
        session: Session, desde: date, hasta: date, agrupacion: str
    ) -> list[VentasPeriodoItem]:
        """Return sales aggregated by the specified time interval."""
        with EstadisticasUnitOfWork(session) as uow:
            rows = uow.estadisticas.get_ventas_periodo(desde, hasta, agrupacion)

            return [
                VentasPeriodoItem(
                    fecha=row["fecha"],
                    total=Decimal(row["total"] or 0),
                )
                for row in rows
            ]

    @staticmethod
    def get_productos_top(
        session: Session, limit: int
    ) -> list[ProductoTopItem]:
        """Return the top N products by revenue (subtotal_snap)."""
        with EstadisticasUnitOfWork(session) as uow:
            rows = uow.estadisticas.get_productos_top(limit)

            return [
                ProductoTopItem(
                    producto_id=row["producto_id"],
                    nombre=row["nombre"],
                    cantidad_vendida=int(row["cantidad_vendida"] or 0),
                    ingresos=Decimal(row["ingresos"] or 0),
                )
                for row in rows
            ]

    @staticmethod
    def get_pedidos_estado(session: Session) -> list[PedidosEstadoItem]:
        """Return order counts grouped by state."""
        with EstadisticasUnitOfWork(session) as uow:
            rows = uow.estadisticas.get_pedidos_por_estado()

            return [
                PedidosEstadoItem(
                    estado_codigo=row["estado_codigo"],
                    cantidad=int(row["cantidad"] or 0),
                )
                for row in rows
            ]

    @staticmethod
    def get_ingresos_forma_pago(
        session: Session, desde: date, hasta: date
    ) -> list[IngresosResponse]:
        """Return revenue grouped by payment method (approved payments only)."""
        with EstadisticasUnitOfWork(session) as uow:
            rows = uow.estadisticas.get_ingresos_por_forma_pago(desde, hasta)

            return [
                IngresosResponse(
                    forma_pago_codigo=row["forma_pago_codigo"],
                    total=Decimal(row["total"] or 0),
                )
                for row in rows
            ]
