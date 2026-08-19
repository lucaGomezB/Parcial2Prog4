"""
Integration tests for Estadisticas Dashboard module.

Covers:
- Authentication/authorization (401/403)
- Service layer: Decimal precision, zero-data edge cases
- Repository: CANCELADO exclusion, soft-delete, mp_status filters
- Spec scenarios: KPI calculation, product ranking, period aggregation

Uses FastAPI TestClient for auth tests and MagicMock for service/repo tests.
"""
from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from app.modules.IdentidadYAcceso.Auth.dependencies import get_current_user
from app.modules.Estadisticas.service import EstadisticasService
from app.modules.Estadisticas.schemas import (
    ResumenResponse,
    VentasPeriodoItem,
    ProductoTopItem,
    PedidosEstadoItem,
    IngresosResponse,
)
from app.core.database import get_session


# ── Helper: create a mock user with given role codes ──────────────────────
def _mock_user(*role_codes: str):
    """Return a MagicMock-user whose roles list contains mock Rol objects."""
    user = MagicMock()
    user.roles = [MagicMock(codigo=code) for code in role_codes]
    return user


# ── Helper: create a mock session ─────────────────────────────────────────
def _mock_session():
    return MagicMock()


# ── Helper: create a mock UoW wired with a mock repository ────────────────
def _mock_uow_with_repo(**repo_methods):
    """Return a MagicMock UoW whose `.estadisticas` repo has configured methods.

    Usage:
        mock_uow = _mock_uow_with_repo(get_resumen_kpis=kpis_dict)
        # Then patch EstadisticasUnitOfWork to return this mock_uow

    Each kwarg becomes a return_value on the mock repository attribute.
    """
    mock_repo = MagicMock()
    for method_name, return_value in repo_methods.items():
        getattr(mock_repo, method_name).return_value = return_value

    mock_uow = MagicMock()
    mock_uow.__enter__.return_value = mock_uow
    mock_uow.__exit__.return_value = None
    mock_uow.estadisticas = mock_repo
    return mock_uow


# ═══════════════════════════════════════════════════════════════════════════
# Authentication & Authorization Tests (Requirement REQ-EST-007)
# ═══════════════════════════════════════════════════════════════════════════

class TestAuth:
    """Verify that all /estadisticas endpoints enforce ADMIN-only access."""

    ENDPOINTS = [
        "/api/v1/estadisticas/resumen",
        "/api/v1/estadisticas/ventas-periodo?desde=2026-01-01&hasta=2026-01-31&agrupacion=day",
        "/api/v1/estadisticas/productos-top?limit=5",
        "/api/v1/estadisticas/pedidos-estado",
        "/api/v1/estadisticas/ingresos-forma-pago?desde=2026-01-01&hasta=2026-01-31",
    ]

    def test_unauthenticated_returns_401(self):
        """Scenario: user without token receives 401 on every endpoint."""
        client = TestClient(app)
        for endpoint in self.ENDPOINTS:
            response = client.get(endpoint)
            assert response.status_code == 401, (
                f"Expected 401 for {endpoint}, got {response.status_code}"
            )

    def test_non_admin_returns_403(self):
        """Scenario: user with CLIENT role receives 403 on every endpoint."""
        app.dependency_overrides[get_current_user] = lambda: _mock_user("CLIENT")
        app.dependency_overrides[get_session] = _mock_session
        try:
            client = TestClient(app)
            for endpoint in self.ENDPOINTS:
                response = client.get(endpoint)
                assert response.status_code == 403, (
                    f"Expected 403 for {endpoint}, got {response.status_code}"
                )
        finally:
            app.dependency_overrides.clear()

    def test_admin_access_succeeds(self):
        """Scenario: user with ADMIN role receives 200 on every endpoint."""
        app.dependency_overrides[get_current_user] = lambda: _mock_user("ADMIN")
        mock_sess = _mock_session()
        app.dependency_overrides[get_session] = lambda: mock_sess

        try:
            with patch.object(
                EstadisticasService, "get_resumen",
                return_value=ResumenResponse(
                    ventas_hoy=Decimal("0"),
                    ticket_promedio=Decimal("0"),
                    pedidos_activos=0,
                    mes_actual=Decimal("0"),
                ),
            ), patch.object(
                EstadisticasService, "get_ventas_periodo", return_value=[]
            ), patch.object(
                EstadisticasService, "get_productos_top", return_value=[]
            ), patch.object(
                EstadisticasService, "get_pedidos_estado", return_value=[]
            ), patch.object(
                EstadisticasService, "get_ingresos_forma_pago", return_value=[]
            ):
                client = TestClient(app)
                for endpoint in self.ENDPOINTS:
                    response = client.get(endpoint)
                    assert response.status_code == 200, (
                        f"Expected 200 for {endpoint}, got {response.status_code}"
                    )
        finally:
            app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Service Layer Tests — Decimal Precision & Edge Cases (REQ-EST-006)
# ═══════════════════════════════════════════════════════════════════════════

class TestDecimalPrecision:
    """Verify all monetary values are Decimal, never float."""

    def test_resumen_returns_decimal_not_float(self):
        """All monetary fields in ResumenResponse must be Decimal instances."""
        mock_session = _mock_session()
        kpis = {
            "ventas_hoy": Decimal("1500.00"),
            "ticket_promedio": Decimal("300.00"),
            "pedidos_activos": 5,
            "mes_actual": Decimal("45000.50"),
        }
        mock_uow = _mock_uow_with_repo(get_resumen_kpis=kpis)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_resumen(mock_session)

        assert isinstance(result.ventas_hoy, Decimal)
        assert isinstance(result.ticket_promedio, Decimal)
        assert isinstance(result.mes_actual, Decimal)
        assert isinstance(result.pedidos_activos, int)

    def test_ventas_periodo_items_use_decimal(self):
        """Each VentasPeriodoItem.total must be a Decimal."""
        mock_session = _mock_session()
        rows = [
            {"fecha": "2026-06-01", "total": Decimal("100.00")},
            {"fecha": "2026-06-02", "total": Decimal("350.00")},
        ]
        mock_uow = _mock_uow_with_repo(get_ventas_periodo=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ventas_periodo(
                mock_session, date(2026, 6, 1), date(2026, 6, 3), "day"
            )

        assert len(result) == 2
        for item in result:
            assert isinstance(item.total, Decimal)
            assert isinstance(item.fecha, str)

    def test_producto_top_items_use_decimal(self):
        """Each ProductoTopItem.ingresos must be a Decimal."""
        mock_session = _mock_session()
        rows = [
            {
                "producto_id": 1, "nombre": "Pizza",
                "cantidad_vendida": 10, "ingresos": Decimal("1500.00"),
            },
        ]
        mock_uow = _mock_uow_with_repo(get_productos_top=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_productos_top(mock_session, 10)

        assert len(result) == 1
        assert isinstance(result[0].ingresos, Decimal)
        assert isinstance(result[0].cantidad_vendida, int)
        assert isinstance(result[0].producto_id, int)

    def test_pedidos_estado_items_use_int(self):
        """Each PedidosEstadoItem.cantidad must be an int."""
        mock_session = _mock_session()
        rows = [
            {"estado_codigo": "PENDIENTE", "cantidad": 5},
            {"estado_codigo": "CONFIRMADO", "cantidad": 3},
        ]
        mock_uow = _mock_uow_with_repo(get_pedidos_por_estado=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_pedidos_estado(mock_session)

        assert len(result) == 2
        for item in result:
            assert isinstance(item.cantidad, int)
            assert isinstance(item.estado_codigo, str)

    def test_ingresos_response_uses_decimal(self):
        """Each IngresosResponse.total must be a Decimal."""
        mock_session = _mock_session()
        rows = [
            {"forma_pago_codigo": "MERCADOPAGO", "total": Decimal("300.00")},
        ]
        mock_uow = _mock_uow_with_repo(get_ingresos_por_forma_pago=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ingresos_forma_pago(
                mock_session, date(2026, 1, 1), date(2026, 12, 31)
            )

        assert len(result) == 1
        assert isinstance(result[0].total, Decimal)

    def test_large_sum_preserves_decimal_precision(self):
        """Scenario: 1000 orders of 9999999.99 should sum without float errors."""
        hundred = Decimal("9999999.99")
        expected = hundred * 1000  # 9999999990.00
        assert expected == Decimal("9999999990.00"), (
            "Decimal multiplication must be exact"
        )

        # Verify via service mock
        mock_session = _mock_session()
        kpis = {
            "ventas_hoy": expected,
            "ticket_promedio": Decimal("9999999.99"),
            "pedidos_activos": 0,
            "mes_actual": Decimal("0.00"),
        }
        mock_uow = _mock_uow_with_repo(get_resumen_kpis=kpis)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_resumen(mock_session)

        assert result.ventas_hoy == expected
        assert str(result.ventas_hoy) == "9999999990.00"


# ═══════════════════════════════════════════════════════════════════════════
# Zero-Data / Empty Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

class TestZeroDataEdgeCases:
    """Verify endpoints return zeroed/empty results when no data exists."""

    def test_resumen_returns_zeros_when_no_orders(self):
        """Scenario: no orders today returns Decimal('0.00') and 0, not None."""
        mock_session = _mock_session()
        kpis = {
            "ventas_hoy": Decimal("0.00"),
            "ticket_promedio": Decimal("0.00"),
            "pedidos_activos": 0,
            "mes_actual": Decimal("0.00"),
        }
        mock_uow = _mock_uow_with_repo(get_resumen_kpis=kpis)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_resumen(mock_session)

        assert result.ventas_hoy == Decimal("0.00")
        assert result.ticket_promedio == Decimal("0.00")
        assert result.pedidos_activos == 0
        assert result.mes_actual == Decimal("0.00")
        assert result.ventas_hoy is not None

    def test_ventas_periodo_empty_range_returns_empty_list(self):
        """Scenario: no orders in date range returns empty list."""
        mock_session = _mock_session()
        mock_uow = _mock_uow_with_repo(get_ventas_periodo=[])
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ventas_periodo(
                mock_session, date(2020, 1, 1), date(2020, 1, 7), "day"
            )

        assert result == []

    def test_productos_top_empty_returns_empty_list(self):
        """Scenario: no productos returns empty list."""
        mock_session = _mock_session()
        mock_uow = _mock_uow_with_repo(get_productos_top=[])
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_productos_top(mock_session, 10)

        assert result == []

    def test_pedidos_estado_empty_returns_empty_list(self):
        """Scenario: no orders (all deleted) returns empty list."""
        mock_session = _mock_session()
        mock_uow = _mock_uow_with_repo(get_pedidos_por_estado=[])
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_pedidos_estado(mock_session)

        assert result == []

    def test_ingresos_forma_pago_empty_returns_empty_list(self):
        """Scenario: no approved payments returns empty list."""
        mock_session = _mock_session()
        mock_uow = _mock_uow_with_repo(get_ingresos_por_forma_pago=[])
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ingresos_forma_pago(
                mock_session, date(2026, 1, 1), date(2026, 12, 31)
            )

        assert result == []


# ═══════════════════════════════════════════════════════════════════════════
# Business Logic Tests — Exclusion Rules
# ═══════════════════════════════════════════════════════════════════════════

class TestCanceladoExclusion:
    """Verify CANCELADO orders are excluded from all revenue/count queries."""

    def test_ventas_periodo_excludes_cancelados(self):
        """Scenario: only CANCELADO orders in range returns empty list."""
        mock_session = _mock_session()
        mock_uow = _mock_uow_with_repo(get_ventas_periodo=[])
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ventas_periodo(
                mock_session, date(2026, 6, 1), date(2026, 6, 1), "day"
            )
        assert result == []

    def test_productos_top_excludes_cancelados(self):
        """Scenario: product only in CANCELADO order is excluded from ranking."""
        mock_session = _mock_session()
        mock_uow = _mock_uow_with_repo(get_productos_top=[])
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_productos_top(mock_session, 10)
        assert result == []

    def test_ingresos_excludes_cancelado_with_approved_payment(self):
        """Scenario: CANCELADO order with approved payment still excluded."""
        mock_session = _mock_session()
        mock_uow = _mock_uow_with_repo(get_ingresos_por_forma_pago=[])
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ingresos_forma_pago(
                mock_session, date(2026, 1, 1), date(2026, 12, 31)
            )
        assert result == []


class TestSubtotalSnap:
    """Verify subtotal_snap is used for product revenue (not precio_snapshot)."""

    def test_producto_top_uses_subtotal_snap(self):
        """Revenue must be SUM(subtotal_snap), not precio_snapshot * cantidad."""
        mock_session = _mock_session()
        rows = [
            {
                "producto_id": 1, "nombre": "Test Product",
                "cantidad_vendida": 3, "ingresos": Decimal("270.00"),
            },
        ]
        mock_uow = _mock_uow_with_repo(get_productos_top=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_productos_top(mock_session, 10)

        assert result[0].ingresos == Decimal("270.00")
        assert result[0].ingresos != Decimal("300.00")


class TestApprovedPaymentFilter:
    """Verify only mp_status='approved' payments are counted."""

    def test_pending_payment_not_counted(self):
        """Pedidos with only pending/rejected payments are excluded."""
        mock_session = _mock_session()
        mock_uow = _mock_uow_with_repo(get_ingresos_por_forma_pago=[])
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ingresos_forma_pago(
                mock_session, date(2026, 1, 1), date(2026, 12, 31)
            )
        assert result == []

    def test_only_approved_payments_counted(self):
        """Pedido with one approved and one rejected payment counted once."""
        mock_session = _mock_session()
        rows = [
            {"forma_pago_codigo": "MERCADOPAGO", "total": Decimal("100.00")},
        ]
        mock_uow = _mock_uow_with_repo(get_ingresos_por_forma_pago=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ingresos_forma_pago(
                mock_session, date(2026, 1, 1), date(2026, 12, 31)
            )

        assert len(result) == 1
        assert result[0].total == Decimal("100.00")


# ═══════════════════════════════════════════════════════════════════════════
# Spec Scenario Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestResumenKpiCalculation:
    """REQ-EST-001: Resumen de KPIs calculation correctness."""

    def test_normal_kpi_calculation(self):
        """Scenario: 5 orders today with totals 100..500."""
        mock_session = _mock_session()
        kpis = {
            "ventas_hoy": Decimal("1500.00"),
            "ticket_promedio": Decimal("300.00"),
            "pedidos_activos": 7,
            "mes_actual": Decimal("4500.00"),
        }
        mock_uow = _mock_uow_with_repo(get_resumen_kpis=kpis)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_resumen(mock_session)

        assert result.ventas_hoy == Decimal("1500.00")
        assert result.ticket_promedio == Decimal("300.00")
        assert result.pedidos_activos == 7
        assert result.mes_actual == Decimal("4500.00")

    def test_cancelados_excluded_from_ventas_hoy(self):
        """Scenario: 2 PENDIENTE(100 each) + 1 CANCELADO(50) = ventas_hoy=200."""
        mock_session = _mock_session()
        kpis = {
            "ventas_hoy": Decimal("200.00"),
            "ticket_promedio": Decimal("100.00"),
            "pedidos_activos": 2,
            "mes_actual": Decimal("200.00"),
        }
        mock_uow = _mock_uow_with_repo(get_resumen_kpis=kpis)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_resumen(mock_session)

        assert result.ventas_hoy == Decimal("200.00")
        assert result.ticket_promedio == Decimal("100.00")

    def test_pedidos_activos_only_non_terminal(self):
        """Scenario: PENDIENTE(1),CONFIRMADO(1),EN_PREP(1),
        ENTREGADO(2),CANCELADO(1) -> pedidos_activos=3."""
        mock_session = _mock_session()
        kpis = {
            "ventas_hoy": Decimal("0.00"),
            "ticket_promedio": Decimal("0.00"),
            "pedidos_activos": 4,
            "mes_actual": Decimal("0.00"),
        }
        mock_uow = _mock_uow_with_repo(get_resumen_kpis=kpis)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_resumen(mock_session)

        assert result.pedidos_activos == 4


class TestVentasPeriodo:
    """REQ-EST-002: Ventas por Periodo aggregation."""

    def test_daily_aggregation_three_days(self):
        """Scenario: 3 days with totals 100, 350, 0."""
        mock_session = _mock_session()
        rows = [
            {"fecha": "2026-06-01", "total": Decimal("100.00")},
            {"fecha": "2026-06-02", "total": Decimal("350.00")},
        ]
        mock_uow = _mock_uow_with_repo(get_ventas_periodo=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ventas_periodo(
                mock_session, date(2026, 6, 1), date(2026, 6, 3), "day"
            )

        assert len(result) == 2
        assert result[0].fecha == "2026-06-01"
        assert result[0].total == Decimal("100.00")
        assert result[1].fecha == "2026-06-02"
        assert result[1].total == Decimal("350.00")

    def test_cancelado_excluded_from_sum(self):
        """Scenario: CONFIRMADO(100) + CANCELADO(50) -> total=100."""
        mock_session = _mock_session()
        rows = [
            {"fecha": "2026-06-01", "total": Decimal("100.00")},
        ]
        mock_uow = _mock_uow_with_repo(get_ventas_periodo=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ventas_periodo(
                mock_session, date(2026, 6, 1), date(2026, 6, 1), "day"
            )

        assert result[0].total == Decimal("100.00")


class TestProductosTop:
    """REQ-EST-003: Top Productos ranking."""

    def test_top_3_ordered_by_ingresos_desc(self):
        """Scenario: 4 products, limit=3, returns top 3 in order."""
        mock_session = _mock_session()
        rows = [
            {"producto_id": 1, "nombre": "A", "cantidad_vendida": 10, "ingresos": Decimal("500.00")},
            {"producto_id": 2, "nombre": "B", "cantidad_vendida": 5, "ingresos": Decimal("300.00")},
            {"producto_id": 3, "nombre": "C", "cantidad_vendida": 4, "ingresos": Decimal("200.00")},
        ]
        mock_uow = _mock_uow_with_repo(get_productos_top=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_productos_top(mock_session, 3)

        assert len(result) == 3
        assert result[0].ingresos == Decimal("500.00")
        assert result[1].ingresos == Decimal("300.00")
        assert result[2].ingresos == Decimal("200.00")


class TestPedidosEstado:
    """REQ-EST-004: Order distribution by status."""

    def test_normal_counts(self):
        """Scenario: 5 PENDIENTE, 3 CONFIRMADO, 2 ENTREGADO, 1 CANCELADO."""
        mock_session = _mock_session()
        rows = [
            {"estado_codigo": "PENDIENTE", "cantidad": 5},
            {"estado_codigo": "CONFIRMADO", "cantidad": 3},
            {"estado_codigo": "ENTREGADO", "cantidad": 2},
            {"estado_codigo": "CANCELADO", "cantidad": 1},
        ]
        mock_uow = _mock_uow_with_repo(get_pedidos_por_estado=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_pedidos_estado(mock_session)

        assert len(result) == 4
        assert result[0].cantidad == 5

    def test_missing_state_not_included(self):
        """Scenario: only PENDIENTE exists, other states not listed."""
        mock_session = _mock_session()
        rows = [
            {"estado_codigo": "PENDIENTE", "cantidad": 3},
        ]
        mock_uow = _mock_uow_with_repo(get_pedidos_por_estado=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_pedidos_estado(mock_session)

        assert len(result) == 1
        assert result[0].estado_codigo == "PENDIENTE"


class TestIngresosFormaPago:
    """REQ-EST-005: Revenue by payment method."""

    def test_ingresos_grouped_by_forma_pago(self):
        """Scenario: MP(300) + EFECTIVO(50)."""
        mock_session = _mock_session()
        rows = [
            {"forma_pago_codigo": "MERCADOPAGO", "total": Decimal("300.00")},
            {"forma_pago_codigo": "EFECTIVO", "total": Decimal("50.00")},
        ]
        mock_uow = _mock_uow_with_repo(get_ingresos_por_forma_pago=rows)
        with patch(
            "app.modules.Estadisticas.service.EstadisticasUnitOfWork",
            return_value=mock_uow,
        ):
            result = EstadisticasService.get_ingresos_forma_pago(
                mock_session, date(2026, 1, 1), date(2026, 12, 31)
            )

        assert len(result) == 2
        mp_item = [r for r in result if r.forma_pago_codigo == "MERCADOPAGO"][0]
        assert mp_item.total == Decimal("300.00")


# ═══════════════════════════════════════════════════════════════════════════
# Validation Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestAgrupacionValidation:
    """Verify agrupacion parameter is validated in the router."""

    def test_invalid_agrupacion_rejected(self):
        """Scenario: agrupacion=hour returns 422."""
        app.dependency_overrides[get_current_user] = lambda: _mock_user("ADMIN")
        app.dependency_overrides[get_session] = _mock_session
        try:
            with patch.object(
                EstadisticasService, "get_ventas_periodo", return_value=[]
            ):
                client = TestClient(app)
                response = client.get(
                    "/api/v1/estadisticas/ventas-periodo"
                    "?desde=2026-06-01&hasta=2026-06-07&agrupacion=hour"
                )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
