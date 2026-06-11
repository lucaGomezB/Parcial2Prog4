"""
Tests for PagoService — MercadoPago payment service.

These tests verify that the service methods:
- Correctly create Pago records with pending status
- Properly update payment status from webhook callbacks
- Correctly read payments by pedido
- Follow the UoW pattern for writes and repository-only for reads
"""
from unittest.mock import MagicMock, patch, PropertyMock
from decimal import Decimal
import uuid
import pytest
from sqlmodel import Session

from modules.VentasPagosTrazabilidad.Pago.service import PagoService
from modules.VentasPagosTrazabilidad.Pago.repository import PagoRepository
from modules.VentasPagosTrazabilidad.Pago.schemas import PagoRead


def _make_uow_mock():
    """Create a properly configured UoW mock.

    MagicMock.__enter__() returns a DIFFERENT mock by default, which breaks
    the 'with ... as uow' pattern. This helper ensures __enter__ returns
    the same mock so that all attribute access on 'uow' resolves correctly.
    """
    mock = MagicMock()
    mock.__enter__.return_value = mock
    return mock


class TestInitMpPayment:
    """PagoService.init_mp_payment creates a Pago record with pending status."""

    def test_creates_pago_record_with_pending_status(self):
        """init_mp_payment creates a Pago with mp_status='pending' and returns PagoRead."""
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()
        mock_repo = MagicMock(spec=PagoRepository)
        mock_uow.pagos = mock_repo

        # Patch PagoRepository to return empty (no existing payment for idempotency check)
        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
        ) as mock_repo_class:
            mock_repo_instance = MagicMock(spec=PagoRepository)
            mock_repo_instance.get_by_pedido.return_value = []
            mock_repo_class.return_value = mock_repo_instance

            # Patch Pago to avoid SQLAlchemy mapper configuration
            with patch(
                "modules.VentasPagosTrazabilidad.Pago.service.Pago",
            ) as mock_pago_class:
                mock_pago_instance = MagicMock()
                mock_pago_instance.id = 1
                mock_pago_instance.pedido_id = 42
                mock_pago_instance.mp_status = "pending"
                mock_pago_instance.mp_payment_id = None
                mock_pago_instance.mp_status_detail = None
                mock_pago_instance.external_reference = "test-uuid-ext"
                mock_pago_instance.idempotency_key = "test-uuid-idem"
                mock_pago_instance.transaction_amount = Decimal("150.00")
                mock_pago_instance.payment_method_id = None
                mock_pago_instance.created_at = MagicMock()
                mock_pago_instance.updated_at = MagicMock()
                mock_pago_class.return_value = mock_pago_instance

                mock_uow.refresh.return_value = mock_pago_instance

                with patch(
                    "modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
                    return_value=mock_uow,
                ):
                    with patch(
                        "modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
                        return_value=MagicMock(
                            total=Decimal("150.00"),
                            forma_pago_codigo="MERCADOPAGO",
                        ),
                    ):
                        result = PagoService.init_mp_payment(mock_session, pedido_id=42)

        assert isinstance(result, PagoRead)
        assert result.mp_status == "pending"
        assert result.pedido_id == 42
        assert result.transaction_amount == 150.0
        mock_uow.add.assert_called_once()

    def test_raises_if_pedido_not_found(self):
        """init_mp_payment raises ValueError when pedido does not exist."""
        mock_session = MagicMock(spec=Session)

        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
            return_value=None,
        ):
            with pytest.raises(ValueError, match="Pedido 99 no encontrado"):
                PagoService.init_mp_payment(mock_session, pedido_id=99)

    def test_accepts_existing_uow_parameter(self):
        """init_mp_payment uses the provided uow instead of creating a new one."""
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()
        mock_repo = MagicMock(spec=PagoRepository)
        mock_uow.pagos = mock_repo

        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
        ) as mock_repo_class:
            mock_repo_instance = MagicMock(spec=PagoRepository)
            mock_repo_instance.get_by_pedido.return_value = []
            mock_repo_class.return_value = mock_repo_instance

            with patch(
                "modules.VentasPagosTrazabilidad.Pago.service.Pago",
            ) as mock_pago_class:
                mock_pago_instance = MagicMock()
                mock_pago_instance.id = 10
                mock_pago_instance.pedido_id = 7
                mock_pago_instance.mp_status = "pending"
                mock_pago_instance.mp_payment_id = None
                mock_pago_instance.mp_status_detail = None
                mock_pago_instance.external_reference = "ext-uow"
                mock_pago_instance.idempotency_key = "idem-uow"
                mock_pago_instance.transaction_amount = Decimal("200.00")
                mock_pago_instance.payment_method_id = None
                mock_pago_instance.created_at = MagicMock()
                mock_pago_instance.updated_at = MagicMock()
                mock_pago_class.return_value = mock_pago_instance
                mock_uow.refresh.return_value = mock_pago_instance

                with patch(
                    "modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
                    return_value=MagicMock(total=Decimal("200.00")),
                ):
                    result = PagoService.init_mp_payment(
                        mock_session, pedido_id=7, uow=mock_uow
                    )

        assert isinstance(result, PagoRead)
        assert result.pedido_id == 7
        assert result.mp_status == "pending"
        # The provided uow should have been used
        mock_uow.add.assert_called_once()
        mock_uow.refresh.assert_called_once()

    def test_generates_unique_uuids_per_call(self):
        """Each call generates different external_reference and idempotency_key."""
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()

        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
        ) as mock_repo_class:
            mock_repo_instance = MagicMock(spec=PagoRepository)
            mock_repo_instance.get_by_pedido.return_value = []
            mock_repo_class.return_value = mock_repo_instance

            with patch(
                "modules.VentasPagosTrazabilidad.Pago.service.Pago",
            ) as mock_pago_class:
                mock_pago_instance = MagicMock()
                mock_pago_instance.mp_status = "pending"
                mock_pago_instance.mp_status_detail = None
                mock_pago_instance.external_reference = "ext-placeholder"
                mock_pago_instance.idempotency_key = "idem-placeholder"
                mock_pago_instance.payment_method_id = None
                mock_pago_instance.transaction_amount = Decimal("100.00")
                mock_pago_instance.pedido_id = 1
                mock_pago_instance.id = 1
                mock_pago_instance.created_at = MagicMock()
                mock_pago_instance.updated_at = MagicMock()
                mock_pago_class.return_value = mock_pago_instance
                mock_uow.refresh.return_value = mock_pago_instance

                with patch(
                    "modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
                    return_value=mock_uow,
                ):
                    with patch(
                        "modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
                        return_value=MagicMock(
                            total=Decimal("100.00"),
                            forma_pago_codigo="MERCADOPAGO",
                        ),
                    ):
                        PagoService.init_mp_payment(mock_session, pedido_id=1)
                        PagoService.init_mp_payment(mock_session, pedido_id=1)

        # Verify Pago was constructed twice with different UUIDs
        assert mock_pago_class.call_count == 2
        call1_kwargs = mock_pago_class.call_args_list[0][1]
        call2_kwargs = mock_pago_class.call_args_list[1][1]
        assert call1_kwargs["external_reference"] != call2_kwargs["external_reference"]
        assert call1_kwargs["idempotency_key"] != call2_kwargs["idempotency_key"]


class TestUpdatePagoStatus:
    """PagoService.update_pago_status updates a Pago record from webhook data."""

    def test_updates_status_from_webhook(self):
        """update_pago_status sets mp_status and mp_status_detail on existing Pago."""
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()
        mock_repo = MagicMock(spec=PagoRepository)
        mock_uow.pagos = mock_repo

        existing_pago = MagicMock()
        existing_pago.id = 5
        existing_pago.pedido_id = 42
        existing_pago.mp_payment_id = None
        existing_pago.mp_status = "pending"
        existing_pago.mp_status_detail = None
        existing_pago.external_reference = "ext-ref-1"
        existing_pago.idempotency_key = "idem-key-1"
        existing_pago.payment_method_id = None
        existing_pago.transaction_amount = Decimal("150.00")
        existing_pago.created_at = MagicMock()
        existing_pago.updated_at = MagicMock()
        mock_repo.get_by_mp_payment_id.return_value = existing_pago

        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
            return_value=mock_uow,
        ):
            result = PagoService.update_pago_status(
                mock_session,
                mp_payment_id=12345,
                mp_status="approved",
                mp_status_detail="accredited",
            )

        assert result.mp_status == "approved"
        assert result.mp_status_detail == "accredited"
        assert result.mp_payment_id == 12345
        assert result.external_reference == "ext-ref-1"
        mock_uow.add.assert_called_once_with(existing_pago)

    def test_raises_if_mp_payment_not_found(self):
        """update_pago_status raises ValueError when mp_payment_id not found."""
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()
        mock_repo = MagicMock(spec=PagoRepository)
        mock_uow.pagos = mock_repo
        mock_repo.get_by_mp_payment_id.return_value = None

        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
            return_value=mock_uow,
        ):
            with pytest.raises(ValueError, match="Pago con MP ID 99999 no encontrado"):
                PagoService.update_pago_status(
                    mock_session,
                    mp_payment_id=99999,
                    mp_status="rejected",
                    mp_status_detail="cc_rejected_other_reason",
                )

    def test_updates_from_pending_to_rejected(self):
        """update_pago_status transitions from pending to rejected correctly."""
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()
        mock_repo = MagicMock(spec=PagoRepository)
        mock_uow.pagos = mock_repo

        existing_pago = MagicMock()
        existing_pago.id = 10
        existing_pago.pedido_id = 10
        existing_pago.mp_payment_id = None
        existing_pago.mp_status = "pending"
        existing_pago.mp_status_detail = None
        existing_pago.external_reference = "ext-ref-2"
        existing_pago.idempotency_key = "idem-key-2"
        existing_pago.payment_method_id = None
        existing_pago.transaction_amount = Decimal("200.00")
        existing_pago.created_at = MagicMock()
        existing_pago.updated_at = MagicMock()
        mock_repo.get_by_mp_payment_id.return_value = existing_pago

        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
            return_value=mock_uow,
        ):
            result = PagoService.update_pago_status(
                mock_session,
                mp_payment_id=888,
                mp_status="rejected",
                mp_status_detail="insufficient_amount",
            )

        assert result.mp_status == "rejected"
        assert result.mp_status_detail == "insufficient_amount"
        assert result.mp_payment_id == 888


class TestGetPagosByPedido:
    """PagoService.get_pagos_by_pedido lists payments for an order (read-only)."""

    def test_delegates_to_repository(self):
        """get_pagos_by_pedido calls repository.get_by_pedido and returns PagoRead list."""
        mock_session = MagicMock(spec=Session)
        mock_repo = MagicMock(spec=PagoRepository)

        mock_pago = MagicMock()
        mock_pago.id = 1
        mock_pago.pedido_id = 42
        mock_pago.mp_status = "approved"
        mock_pago.mp_payment_id = 12345
        mock_pago.mp_status_detail = "accredited"
        mock_pago.external_reference = "ext-uuid-1"
        mock_pago.idempotency_key = "idem-uuid-1"
        mock_pago.transaction_amount = Decimal("100.00")
        mock_pago.payment_method_id = "visa"
        mock_pago.created_at = MagicMock()
        mock_pago.updated_at = MagicMock()

        mock_repo.get_by_pedido.return_value = [mock_pago]

        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
            return_value=mock_repo,
        ):
            results = PagoService.get_pagos_by_pedido(mock_session, pedido_id=42)

        assert len(results) == 1
        assert isinstance(results[0], PagoRead)
        assert results[0].pedido_id == 42
        assert results[0].mp_status == "approved"
        mock_repo.get_by_pedido.assert_called_once_with(42)

    def test_returns_empty_list_when_no_payments(self):
        """get_pagos_by_pedido returns empty list when no payments exist."""
        mock_session = MagicMock(spec=Session)
        mock_repo = MagicMock(spec=PagoRepository)
        mock_repo.get_by_pedido.return_value = []

        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
            return_value=mock_repo,
        ):
            results = PagoService.get_pagos_by_pedido(mock_session, pedido_id=999)

        assert results == []
        mock_repo.get_by_pedido.assert_called_once_with(999)

    def test_does_not_use_uow_read_only(self):
        """get_pagos_by_pedido does not create a UoW (read-only operation)."""
        mock_session = MagicMock(spec=Session)
        mock_repo = MagicMock(spec=PagoRepository)
        mock_repo.get_by_pedido.return_value = []

        with patch(
            "modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
            return_value=mock_repo,
        ):
            PagoService.get_pagos_by_pedido(mock_session, pedido_id=1)

        # Only repository is used — no UoW context manager created
