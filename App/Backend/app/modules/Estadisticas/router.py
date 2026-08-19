"""
Estadisticas router — analytics dashboard endpoints.

All endpoints require ADMIN role. All monetary values are Decimal(10,2).
Query parameters use Python date for desde/hasta.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import AdminOnly
from app.modules.IdentidadYAcceso.Auth.dependencies import require_roles

from .service import EstadisticasService
from .schemas import (
    ResumenResponse,
    VentasPeriodoItem,
    ProductoTopItem,
    PedidosEstadoItem,
    IngresosResponse,
)


router = APIRouter(prefix="/estadisticas", tags=["Estadisticas"])

# Valid agrupacion values for ventas-periodo endpoint
_VALID_AGRUPACION = frozenset({"day", "week", "month"})


def _validate_agrupacion(agrupacion: str) -> None:
    """Raise 422 if agrupacion is not one of day, week, month."""
    if agrupacion not in _VALID_AGRUPACION:
        sorted_vals = ", ".join(sorted(_VALID_AGRUPACION))
        raise HTTPException(
            status_code=422,
            detail={
                "mensaje": (
                    f"agrupacion '{agrupacion}' no es valida. "
                    f"Valores aceptados: {sorted_vals}"
                ),
                "errors": [
                    {
                        "loc": ["query", "agrupacion"],
                        "msg": f"Value must be one of: {sorted_vals}",
                        "type": "value_error",
                    }
                ],
            },
        )


@router.get(
    "/resumen",
    response_model=ResumenResponse,
    dependencies=[Depends(require_roles(AdminOnly))],
)
def resumen(session: Session = Depends(get_session)) -> ResumenResponse:
    """GET /estadisticas/resumen — KPI summary: ventas hoy, ticket promedio,
    pedidos activos, total mes actual.

    Excludes CANCELADO orders and soft-deleted records from all calculations.
    pedidos_activos counts only non-terminal states (PENDIENTE, CONFIRMADO,
    EN_PREP).
    """
    return EstadisticasService.get_resumen(session)


@router.get(
    "/ventas-periodo",
    response_model=list[VentasPeriodoItem],
    dependencies=[Depends(require_roles(AdminOnly))],
)
def ventas_periodo(
    desde: date = Query(..., description="Start date (YYYY-MM-DD)"),
    hasta: date = Query(..., description="End date (YYYY-MM-DD)"),
    agrupacion: str = Query(..., description="day | week | month"),
    session: Session = Depends(get_session),
) -> list[VentasPeriodoItem]:
    """GET /estadisticas/ventas-periodo — Aggregated sales over a date range,
    grouped by the specified interval.

    Query params:
        desde: start date (inclusive, BETWEEN)
        hasta: end date (inclusive, BETWEEN)
        agrupacion: one of day, week, month
    """
    _validate_agrupacion(agrupacion)
    return EstadisticasService.get_ventas_periodo(
        session, desde, hasta, agrupacion
    )


@router.get(
    "/productos-top",
    response_model=list[ProductoTopItem],
    dependencies=[Depends(require_roles(AdminOnly))],
)
def productos_top(
    limit: int = Query(10, ge=1, description="Max results (default 10)"),
    session: Session = Depends(get_session),
) -> list[ProductoTopItem]:
    """GET /estadisticas/productos-top?limit=10 — Top products by revenue.

    Revenue is calculated from subtotal_snap (NOT precio_snapshot).
    Excludes CANCELADO orders and soft-deleted records.
    """
    return EstadisticasService.get_productos_top(session, limit)


@router.get(
    "/pedidos-estado",
    response_model=list[PedidosEstadoItem],
    dependencies=[Depends(require_roles(AdminOnly))],
)
def pedidos_estado(
    session: Session = Depends(get_session),
) -> list[PedidosEstadoItem]:
    """GET /estadisticas/pedidos-estado — Order counts grouped by estado_codigo.

    Excludes soft-deleted orders. States with zero orders are not included.
    Results ordered by count descending.
    """
    return EstadisticasService.get_pedidos_estado(session)


@router.get(
    "/ingresos-forma-pago",
    response_model=list[IngresosResponse],
    dependencies=[Depends(require_roles(AdminOnly))],
)
def ingresos_forma_pago(
    desde: date = Query(..., description="Start date (YYYY-MM-DD)"),
    hasta: date = Query(..., description="End date (YYYY-MM-DD)"),
    session: Session = Depends(get_session),
) -> list[IngresosResponse]:
    """GET /estadisticas/ingresos-forma-pago — Revenue by payment method.

    For MERCADOPAGO: only counts pedidos with mp_status='approved'.
    For PAGO_LOCAL and EFECTIVO: counts all confirmed orders.
    Excludes PENDIENTE, CANCELADO, and soft-deleted records.
    """
    return EstadisticasService.get_ingresos_forma_pago(session, desde, hasta)
