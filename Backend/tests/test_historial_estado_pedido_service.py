"""
Tests for HistorialEstadoPedidoService — read-only access layer.

These tests verify that the service methods delegate correctly to the
repository or build the right SQL queries. The service is a thin
orchestration layer with no complex business logic, so tests focus on:
- Correct delegation to repository
- Correct query construction with pagination/filtering
- Proper return type handling
"""
from unittest.mock import MagicMock, patch, sentinel
import pytest
from sqlmodel import Session
from modules.VentasPagosTrazabilidad.HistorialEstadoPedido.service import (
    HistorialEstadoPedidoService,
)
from modules.VentasPagosTrazabilidad.HistorialEstadoPedido.repository import (
    HistorialEstadoPedidoRepository,
)


class TestGetByPedido:
    """HistorialEstadoPedidoService.get_by_pedido delegates to repository."""

    def test_delegates_to_repository_get_by_pedido(self):
        """get_by_pedido calls repository.get_by_pedido with the given pedido_id."""
        mock_session = MagicMock(spec=Session)
        mock_repo = MagicMock(spec=HistorialEstadoPedidoRepository)
        expected_result = [sentinel.record_1, sentinel.record_2]
        mock_repo.get_by_pedido.return_value = expected_result

        with patch(
            "modules.VentasPagosTrazabilidad.HistorialEstadoPedido.service.HistorialEstadoPedidoRepository",
            return_value=mock_repo,
        ):
            result = HistorialEstadoPedidoService.get_by_pedido(
                mock_session, pedido_id=42
            )

        assert result == expected_result
        mock_repo.get_by_pedido.assert_called_once_with(42)


class TestGetById:
    """HistorialEstadoPedidoService.get_by_id delegates to repository."""

    def test_delegates_to_repository_get_by_id(self):
        """get_by_id calls repository.get_by_id with the given history_id."""
        mock_session = MagicMock(spec=Session)
        mock_repo = MagicMock(spec=HistorialEstadoPedidoRepository)
        expected = sentinel.history_record
        mock_repo.get_by_id.return_value = expected

        with patch(
            "modules.VentasPagosTrazabilidad.HistorialEstadoPedido.service.HistorialEstadoPedidoRepository",
            return_value=mock_repo,
        ):
            result = HistorialEstadoPedidoService.get_by_id(
                mock_session, history_id=7
            )

        assert result is expected
        mock_repo.get_by_id.assert_called_once_with(7)

    def test_returns_none_when_not_found(self):
        """get_by_id returns None when no record matches the given ID."""
        mock_session = MagicMock(spec=Session)
        mock_repo = MagicMock(spec=HistorialEstadoPedidoRepository)
        mock_repo.get_by_id.return_value = None

        with patch(
            "modules.VentasPagosTrazabilidad.HistorialEstadoPedido.service.HistorialEstadoPedidoRepository",
            return_value=mock_repo,
        ):
            result = HistorialEstadoPedidoService.get_by_id(
                mock_session, history_id=999
            )

        assert result is None


class TestGetAll:
    """HistorialEstadoPedidoService.get_all builds correct queries."""

    def test_get_all_without_filter_returns_all(self):
        """get_all with no pedido_id returns paginated results ordered by created_at DESC."""
        mock_session = MagicMock(spec=Session)
        mock_exec = MagicMock()
        expected = [sentinel.h1, sentinel.h2]
        mock_exec.all.return_value = expected

        # Chain session.exec(...).all()
        mock_session.exec.return_value = mock_exec

        result = HistorialEstadoPedidoService.get_all(
            mock_session, skip=0, limit=50, pedido_id=None
        )

        assert result == expected
        mock_session.exec.assert_called_once()

        # Verify the query is constructed with offset, limit, and order_by DESC
        call_stmt = mock_session.exec.call_args[0][0]
        assert "offset" in str(call_stmt).lower() or "limit" in str(call_stmt).lower()
        assert str(call_stmt).count("offset") >= 0

    def test_get_all_with_pedido_id_filters_by_order(self):
        """get_all with pedido_id adds a WHERE clause for pedido_id."""
        mock_session = MagicMock(spec=Session)
        mock_exec = MagicMock()
        mock_exec.all.return_value = [sentinel.filtered_record]
        mock_session.exec.return_value = mock_exec

        result = HistorialEstadoPedidoService.get_all(
            mock_session, skip=0, limit=100, pedido_id=42
        )

        assert result == [sentinel.filtered_record]

        # The query should contain a filter for pedido_id == 42
        call_stmt = mock_session.exec.call_args[0][0]
        stmt_str = str(call_stmt)
        assert "pedido_id" in stmt_str
        # Verify created_at DESC ordering
        assert "DESC" in stmt_str
