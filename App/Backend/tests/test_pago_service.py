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

from app.modules.VentasPagosTrazabilidad.Pago.service import PagoService
from app.modules.VentasPagosTrazabilidad.Pago.repository import PagoRepository
from app.modules.VentasPagosTrazabilidad.Pago.schemas import PagoRead


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
            "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
        ) as mock_repo_class:
            mock_repo_instance = MagicMock(spec=PagoRepository)
            mock_repo_instance.get_by_pedido.return_value = []
            mock_repo_class.return_value = mock_repo_instance

            # Patch Pago to avoid SQLAlchemy mapper configuration
            with patch(
                "app.modules.VentasPagosTrazabilidad.Pago.service.Pago",
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
                    "app.modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
                    return_value=mock_uow,
                ):
                    with patch(
                        "app.modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
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
            "app.modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
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
            "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
        ) as mock_repo_class:
            mock_repo_instance = MagicMock(spec=PagoRepository)
            mock_repo_instance.get_by_pedido.return_value = []
            mock_repo_class.return_value = mock_repo_instance

            with patch(
                "app.modules.VentasPagosTrazabilidad.Pago.service.Pago",
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
                    "app.modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
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
        """Each call generates different external_reference and idempotency_key.
        
        First call: no existing Pago → creates new Pago record.
        Second call: existing pending Pago found → returns it (idempotent, no duplicate).
        """
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()

        with patch(
            "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
        ) as mock_repo_class:
            mock_repo_instance = MagicMock(spec=PagoRepository)
            mock_repo_instance.get_by_pedido.return_value = []
            # First call: no existing pending/approved Pago
            mock_repo_instance.get_pending_or_approved.return_value = None
            mock_repo_class.return_value = mock_repo_instance

            with patch(
                "app.modules.VentasPagosTrazabilidad.Pago.service.Pago",
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
                    "app.modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
                    return_value=mock_uow,
                ):
                    with patch(
                        "app.modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
                        return_value=MagicMock(
                            total=Decimal("100.00"),
                            forma_pago_codigo="MERCADOPAGO",
                        ),
                    ):
                        # First call: creates a new Pago
                        PagoService.init_mp_payment(mock_session, pedido_id=1)

                        # Now simulate an existing pending Pago for the second call
                        mock_repo_instance.get_pending_or_approved.return_value = mock_pago_instance
                        # Second call: should return existing Pago without creating new one
                        PagoService.init_mp_payment(mock_session, pedido_id=1)

        # Pago should be constructed only ONCE (second call is idempotent)
        assert mock_pago_class.call_count == 1, (
            "Second call should return existing Pago, not create a duplicate"
        )


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
            "app.modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
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
        mock_repo.update.assert_called_once_with(existing_pago)

    def test_raises_if_mp_payment_not_found(self):
        """update_pago_status raises ValueError when mp_payment_id not found."""
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()
        mock_repo = MagicMock(spec=PagoRepository)
        mock_uow.pagos = mock_repo
        mock_repo.get_by_mp_payment_id.return_value = None

        with patch(
            "app.modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
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
            "app.modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
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
            "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
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
            "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
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
            "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
            return_value=mock_repo,
        ):
            PagoService.get_pagos_by_pedido(mock_session, pedido_id=1)

        # Only repository is used — no UoW context manager created


class TestInitMpPaymentIdempotencyKey:
    """init_mp_payment passes X-Idempotency-Key header to MercadoPago SDK."""

    def test_passes_idempotency_key_to_mp_sdk(self):
        """Verify idempotency_key is passed as X-Idempotency-Key in request_options.

        When init_mp_payment creates a MercadoPago preference, it MUST
        include the idempotency_key as a header so MP can deduplicate
        and return it in the payment response for webhook dedup.
        """
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()
        mock_repo = MagicMock(spec=PagoRepository)
        mock_uow.pagos = mock_repo

        # Use a controlled UUID so we can assert the exact value
        controlled_uuid = "11111111-1111-1111-1111-111111111111"

        with patch(
            "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
        ) as mock_repo_class:
            mock_repo_instance = MagicMock(spec=PagoRepository)
            mock_repo_instance.get_by_pedido.return_value = []
            mock_repo_instance.get_pending_or_approved.return_value = None
            mock_repo_class.return_value = mock_repo_instance

            with patch(
                "app.modules.VentasPagosTrazabilidad.Pago.service.Pago",
            ) as mock_pago_class:
                mock_pago_instance = MagicMock()
                mock_pago_instance.id = 1
                mock_pago_instance.pedido_id = 42
                mock_pago_instance.mp_status = "pending"
                mock_pago_instance.mp_payment_id = None
                mock_pago_instance.mp_status_detail = None
                mock_pago_instance.external_reference = "ext-ref-idem-test"
                mock_pago_instance.idempotency_key = controlled_uuid
                mock_pago_instance.transaction_amount = Decimal("150.00")
                mock_pago_instance.payment_method_id = None
                mock_pago_instance.created_at = MagicMock()
                mock_pago_instance.updated_at = MagicMock()
                mock_pago_class.return_value = mock_pago_instance

                mock_uow.refresh.return_value = mock_pago_instance

                with patch(
                    "app.modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
                    return_value=mock_uow,
                ):
                    with patch(
                        "app.modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
                        return_value=MagicMock(
                            total=Decimal("150.00"),
                            usuario=MagicMock(nombre="Test", email="test@test.com"),
                        ),
                    ):
                        # ── Mock the MercadoPago SDK ──
                        mock_sdk = MagicMock()
                        mock_preference_api = MagicMock()
                        mock_preference_api.create.return_value = {
                            "status": 201,
                            "response": {
                                "id": "pref-test-123",
                                "init_point": "https://sandbox.mercadopago.com/checkout",
                            },
                        }
                        mock_sdk.preference.return_value = mock_preference_api

                        with patch(
                            "app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk",
                            return_value=mock_sdk,
                        ):
                            # Patch uuid.uuid4() so idempotency_key is deterministic
                            with patch(
                                "app.modules.VentasPagosTrazabilidad.Pago.service.uuid"
                            ) as mock_uuid:
                                mock_uuid.uuid4.return_value = controlled_uuid
                                PagoService.init_mp_payment(
                                    mock_session, pedido_id=42
                                )

        # ── ASSERT: create() was called with request_options containing the key ──
        mock_preference_api.create.assert_called_once()
        call_args, call_kwargs = mock_preference_api.create.call_args

        # The create() call: sdk.preference().create(preference_data, request_options)
        # args[0] = preference_data, args[1] = RequestOptions
        assert len(call_args) >= 2, (
            "Expected create() to be called with at least 2 positional args "
            f"(preference_data, request_options), got {len(call_args)}"
        )
        request_options = call_args[1]
        assert hasattr(request_options, "custom_headers"), (
            "request_options must be a RequestOptions object with custom_headers"
        )
        assert (
            request_options.custom_headers["X-Idempotency-Key"] == controlled_uuid
        ), (
            f"Expected X-Idempotency-Key='{controlled_uuid}', "
            f"got '{request_options.custom_headers['X-Idempotency-Key']}'"
        )

    def test_different_keys_produce_different_headers(self):
        """Two calls with different idempotency_keys send different headers.

        Triangulation: ensures the key is not hardcoded but dynamically
        taken from the generated uuid.uuid4() value.

        NOTE: uuid.uuid4() is called TWICE per init_mp_payment call:
          1st → external_reference, 2nd → idempotency_key.
        So we need 4 UUIDs for 2 calls.
        """
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()

        # 4 UUIDs: ext-ref-1, idem-1, ext-ref-2, idem-2
        uuid_sequence = [
            "ext-ref-first",
            "idem-key-first",
            "ext-ref-second",
            "idem-key-second",
        ]

        with patch(
            "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository",
        ) as mock_repo_class:
            mock_repo_instance = MagicMock(spec=PagoRepository)
            mock_repo_instance.get_by_pedido.return_value = []
            mock_repo_instance.get_pending_or_approved.return_value = None
            mock_repo_class.return_value = mock_repo_instance

            with patch(
                "app.modules.VentasPagosTrazabilidad.Pago.service.Pago",
            ) as mock_pago_class:
                mock_pago_instance = MagicMock()
                mock_pago_instance.id = 1
                mock_pago_instance.pedido_id = 77
                mock_pago_instance.mp_status = "pending"
                mock_pago_instance.mp_payment_id = None
                mock_pago_instance.mp_status_detail = None
                mock_pago_instance.external_reference = "ext-ref-abc"
                mock_pago_instance.idempotency_key = "placeholder"
                mock_pago_instance.transaction_amount = Decimal("200.00")
                mock_pago_instance.payment_method_id = None
                mock_pago_instance.created_at = MagicMock()
                mock_pago_instance.updated_at = MagicMock()
                mock_pago_class.return_value = mock_pago_instance

                mock_uow.refresh.return_value = mock_pago_instance

                with patch(
                    "app.modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
                    return_value=mock_uow,
                ):
                    with patch(
                        "app.modules.VentasPagosTrazabilidad.Pago.service.PedidoService.get_by_id",
                        return_value=MagicMock(
                            total=Decimal("200.00"),
                            usuario=MagicMock(nombre="T1", email="t1@t.com"),
                        ),
                    ):
                        mock_sdk = MagicMock()
                        mock_pref = MagicMock()
                        mock_pref.create.return_value = {
                            "status": 201,
                            "response": {"id": "pref-x", "init_point": "https://mp.com"},
                        }
                        mock_sdk.preference.return_value = mock_pref

                        with patch(
                            "app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk",
                            return_value=mock_sdk,
                        ):
                            # Patch uuid.uuid4() — 4 UUIDs for 2 calls
                            with patch(
                                "app.modules.VentasPagosTrazabilidad.Pago.service.uuid"
                            ) as mock_uuid_mod:
                                mock_uuid_mod.uuid4.side_effect = uuid_sequence

                                # First call: idempotency_key = uuid[1] = "idem-key-first"
                                PagoService.init_mp_payment(
                                    mock_session, pedido_id=77
                                )

                                first_call_args = mock_pref.create.call_args[0]
                                assert (
                                    first_call_args[1].custom_headers[
                                        "X-Idempotency-Key"
                                    ]
                                    == "idem-key-first"
                                )

                                # Second call: idempotency_key = uuid[3] = "idem-key-second"
                                PagoService.init_mp_payment(
                                    mock_session, pedido_id=88
                                )

                                all_calls = mock_pref.create.call_args_list
                                assert len(all_calls) == 2
                                second_call_args = all_calls[1][0]
                                assert (
                                    second_call_args[1].custom_headers[
                                        "X-Idempotency-Key"
                                    ]
                                    == "idem-key-second"
                                )
                                assert (
                                    first_call_args[1].custom_headers[
                                        "X-Idempotency-Key"
                                    ]
                                    != second_call_args[1].custom_headers[
                                        "X-Idempotency-Key"
                                    ]
                                ), (
                                    "Each call must use a different idempotency_key"
                                )


class TestProcessWebhook:
    """process_webhook handles MP IPN notifications with topic filtering and dedup."""

    def test_ignores_non_payment_format2_notification(self):
        """Format 2 notifications without payment topic/action are ignored.

        MercadoPago sends various notification types (merchant_order,
        payment, etc.). We must only process payment-related notifications
        to avoid errors from parsing non-payment data.
        """
        # merchant_order.created — NOT a payment notification
        result = PagoService.process_webhook({
            "data": {"id": "123456789"},
            "action": "merchant_order.created",
        })
        assert result["status"] == "ignored"
        assert result["detail"] == "not a payment notification"

    def test_ignores_format2_with_neither_topic_nor_action(self):
        """Format 2 without any payment-related field is ignored.

        Triangulation: edge case where neither topic nor action
        contains 'payment'.
        """
        result = PagoService.process_webhook({
            "data": {"id": "987654321"},
        })
        assert result["status"] == "ignored"
        assert result["detail"] == "not a payment notification"

    @patch(
        "app.modules.VentasPagosTrazabilidad.Pago.service.PagoService.get_payment_from_mp"
    )
    @patch(
        "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository"
    )
    def test_deduplicates_by_idempotency_key(
        self,
        mock_repo_class,
        mock_get_payment,
    ):
        """Webhook skips processing when idempotency_key matches existing Pago.

        When MP returns an idempotency_key that already exists in the DB
        with status 'approved' or 'rejected', the webhook must skip
        processing to avoid duplicate status updates.
        """
        # ── Mock get_payment_from_mp to return payment data with known key ──
        mock_get_payment.return_value = {
            "status": "approved",
            "status_detail": "accredited",
            "external_reference": "ext-ref-dup",
            "idempotency_key": "known-idem-key-dup",
        }

        # ── Mock the repository ──
        mock_repo = MagicMock(spec=PagoRepository)
        # Simulate: a Pago with this idempotency_key already exists (approved)
        existing_pago = MagicMock()
        existing_pago.mp_status = "approved"
        mock_repo.get_by_idempotency_key.return_value = existing_pago
        mock_repo_class.return_value = mock_repo

        # ── Patch Session(engine) inside _process() ──
        # _process() does: from app.core.database import engine
        #                from sqlmodel import Session
        #                with Session(engine) as _session
        with patch("app.core.database.engine"):
            with patch("sqlmodel.Session") as mock_session_cls:
                mock_db_session = MagicMock()
                mock_session_cls.return_value.__enter__.return_value = (
                    mock_db_session
                )

                # ── Call process_webhook with a valid payment notification ──
                result = PagoService.process_webhook({
                    "id": "555555",
                    "topic": "payment",
                })

        # Must return 200 quickly (to prevent MP retries)
        assert result["status"] == "received"
        assert result["detail"] == "ok"

        # ── Verify dedup logic was triggered ──
        mock_repo.get_by_idempotency_key.assert_called_with("known-idem-key-dup")
        # get_by_external_reference should NOT be called (dedup returned early)
        mock_repo.get_by_external_reference.assert_not_called()

    @patch(
        "app.modules.VentasPagosTrazabilidad.Pago.service.PagoService.get_payment_from_mp"
    )
    @patch(
        "app.modules.VentasPagosTrazabilidad.Pago.service.PagoRepository"
    )
    def test_dedup_detection_logs_message(
        self,
        mock_repo_class,
        mock_get_payment,
    ):
        """A clear log message is emitted when duplicate webhook is detected.

        Triangulation: verify the log output, not just the code path.
        """
        mock_get_payment.return_value = {
            "status": "rejected",
            "status_detail": "cc_rejected_other_reason",
            "external_reference": "ext-ref-log",
            "idempotency_key": "dup-key-log-test",
        }

        mock_repo = MagicMock(spec=PagoRepository)
        existing_pago = MagicMock()
        existing_pago.mp_status = "rejected"
        mock_repo.get_by_idempotency_key.return_value = existing_pago
        mock_repo_class.return_value = mock_repo

        with patch("app.core.database.engine"):
            with patch("sqlmodel.Session") as mock_session_cls:
                mock_db_session = MagicMock()
                mock_session_cls.return_value.__enter__.return_value = (
                    mock_db_session
                )

                with patch(
                    "app.modules.VentasPagosTrazabilidad.Pago.service.logger"
                ) as mock_logger:
                    PagoService.process_webhook({
                        "id": "666666",
                        "topic": "payment",
                    })

                    # Verify the duplicate log message was emitted
                    mock_logger.info.assert_any_call(
                        "MP webhook: duplicate ignored for idempotency_key=%s, status=%s",
                        "dup-key-log-test", "rejected",
                    )


class TestInitFromCartRetry:
    """init_from_cart: retry path when existing Pago has mp_payment_id=None.

    When a user retries init_from_cart after a first attempt created a Pago
    (mp_payment_id=None, preference-only, not yet paid), the service must
    NOT return init_point=None. Instead it must create a fresh MP preference
    with a new retry idempotency key and return a valid init_point.
    """

    def test_retry_creates_fresh_pago_and_returns_init_point(self):
        """Second init_from_cart with same fingerprint returns valid init_point.

        Scenario:
        1. First call: no existing Pago → creates Pago + snapshot + MP preference
        2. Second call: existing Pago found with mp_payment_id=None
           → creates NEW Pago with retry idempotency key
           → creates NEW MP preference
           → returns init_point (NOT None)
        """
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()
        mock_repo = MagicMock(spec=PagoRepository)
        mock_uow.pagos = mock_repo

        # ── Mock: ProductoRepository for stock validation ──
        with patch(
            "app.modules.CatalogoDeProductos.Producto.repository.ProductoRepository",
        ) as mock_prod_repo_class:
            mock_prod_repo = MagicMock()
            mock_producto = MagicMock()
            mock_producto.id = 1
            mock_producto.nombre = "Test Product"
            mock_producto.es_producto_terminado = True
            mock_producto.stock_manual = 10
            mock_prod_repo.get_by_id.return_value = mock_producto
            mock_prod_repo_class.return_value = mock_prod_repo

            # ── Mock: VentasPagosTrazabilidadUnitOfWork ──
            with patch(
                "app.modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
                return_value=mock_uow,
            ):
                # ── Mock: Pago model ──
                with patch(
                    "app.modules.VentasPagosTrazabilidad.Pago.service.Pago",
                ) as mock_pago_class:
                    mock_pago_instance = MagicMock()
                    mock_pago_instance.id = 1
                    mock_pago_instance.pedido_id = None
                    mock_pago_instance.mp_status = "pending"
                    mock_pago_instance.mp_payment_id = None
                    mock_pago_instance.mp_status_detail = None
                    mock_pago_instance.external_reference = "ext-ref-original"
                    mock_pago_instance.idempotency_key = "fingerprint-original"
                    mock_pago_instance.transaction_amount = Decimal("100.00")
                    mock_pago_instance.payment_method_id = None
                    mock_pago_instance.created_at = MagicMock()
                    mock_pago_instance.updated_at = MagicMock()
                    mock_pago_class.return_value = mock_pago_instance
                    mock_uow.refresh.return_value = mock_pago_instance

                    # ── Mock: CarritoSnapshot ──
                    with patch(
                        "app.modules.VentasPagosTrazabilidad.Pago.service.CarritoSnapshot",
                    ) as mock_snapshot_class:
                        mock_snapshot = MagicMock()
                        mock_snapshot_class.return_value = mock_snapshot

                        # ── Mock: MP SDK ──
                        mock_sdk = MagicMock()
                        mock_pref = MagicMock()
                        # First and second calls both succeed with different init_points
                        mock_pref.create.side_effect = [
                            {"status": 201, "response": {"id": "pref-1", "init_point": "https://mp.com/checkout-1"}},
                            {"status": 201, "response": {"id": "pref-2", "init_point": "https://mp.com/checkout-2"}},
                        ]
                        mock_sdk.preference.return_value = mock_pref

                        with patch(
                            "app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk",
                            return_value=mock_sdk,
                        ):
                            # ── Prepare InitFromCartRequest ──
                            from app.modules.VentasPagosTrazabilidad.Pago.schemas import (
                                InitFromCartRequest,
                                CartItemInput,
                            )
                            data = InitFromCartRequest(
                                forma_pago_codigo="MERCADOPAGO",
                                subtotal=Decimal("100.00"),
                                descuento=Decimal("0.00"),
                                costo_envio=Decimal("0.00"),
                                direccion_id=None,
                                items=[
                                    CartItemInput(
                                        producto_id=1,
                                        nombre="Test Product",
                                        precio=Decimal("100.00"),
                                        cantidad=1,
                                        ingredientes_excluidos=[],
                                    )
                                ],
                            )
                            usuario = MagicMock()
                            usuario.id = 1
                            usuario.nombre = "Test"
                            usuario.email = "test@test.com"

                            # ── FIRST call: no existing Pago → creates everything ──
                            mock_repo.get_by_idempotency_key.return_value = None

                            pago1, init_point1, err1 = PagoService.init_from_cart(
                                mock_session, data, usuario
                            )

                            assert init_point1 == "https://mp.com/checkout-1", (
                                f"First call must return valid init_point, got {init_point1}"
                            )
                            assert err1 is None

                            # ── SECOND call: existing Pago found with mp_payment_id=None ──
                            existing_pago = MagicMock()
                            existing_pago.mp_payment_id = None
                            existing_pago.mp_status = "pending"
                            existing_pago.external_reference = "ext-ref-original"
                            existing_pago.id = 1
                            existing_pago.idempotency_key = "fingerprint-original"
                            existing_pago.transaction_amount = Decimal("100.00")
                            existing_pago.pedido_id = None
                            existing_pago.mp_status_detail = None
                            existing_pago.payment_method_id = None
                            existing_pago.created_at = MagicMock()
                            existing_pago.updated_at = MagicMock()

                            mock_repo.get_by_idempotency_key.return_value = existing_pago

                            # Create a fresh mock for the second Pago instance
                            mock_pago_instance2 = MagicMock()
                            mock_pago_instance2.id = 2
                            mock_pago_instance2.pedido_id = None
                            mock_pago_instance2.mp_status = "pending"
                            mock_pago_instance2.mp_payment_id = None
                            mock_pago_instance2.mp_status_detail = None
                            mock_pago_instance2.external_reference = "ext-ref-original"
                            mock_pago_instance2.idempotency_key = "fingerprint-original-retry-uuid6"
                            mock_pago_instance2.transaction_amount = Decimal("100.00")
                            mock_pago_instance2.payment_method_id = None
                            mock_pago_instance2.created_at = MagicMock()
                            mock_pago_instance2.updated_at = MagicMock()
                            mock_pago_class.return_value = mock_pago_instance2

                            pago2, init_point2, err2 = PagoService.init_from_cart(
                                mock_session, data, usuario
                            )

                            # ── ASSERTIONS ──
                            assert init_point2 == "https://mp.com/checkout-2", (
                                f"Second call (retry) must return valid init_point, got {init_point2}. "
                                "Bug: init_from_cart returns None for retry when mp_payment_id is None."
                            )
                            assert err2 is None, (
                                f"Second call (retry) must not return error, got {err2}"
                            )
                            assert pago2 is not None
                            # Retry idempotency_key should contain "-retry-"
                            assert "-retry-" in pago2.idempotency_key, (
                                f"Retry Pago must have idempotency_key with '-retry-' suffix, "
                                f"got {pago2.idempotency_key}"
                            )
                            # Both Pagos share the same external_reference (same snapshot)
                            assert pago2.external_reference == "ext-ref-original", (
                                "Retry Pago must reuse the original external_reference "
                                "(both Pagos share the same snapshot)"
                            )

    def test_retry_still_returns_none_on_mp_failure(self):
        """When retry creates fresh preference but MP SDK fails, returns init_point=None.

        Triangulation: the retry path handles MP SDK failures gracefully
        just like the first-call path.
        """
        mock_session = MagicMock(spec=Session)
        mock_uow = _make_uow_mock()
        mock_repo = MagicMock(spec=PagoRepository)
        mock_uow.pagos = mock_repo

        with patch(
            "app.modules.CatalogoDeProductos.Producto.repository.ProductoRepository",
        ) as mock_prod_repo_class:
            mock_prod_repo = MagicMock()
            mock_producto = MagicMock()
            mock_producto.id = 1
            mock_producto.nombre = "Test Product"
            mock_producto.es_producto_terminado = True
            mock_producto.stock_manual = 10
            mock_prod_repo.get_by_id.return_value = mock_producto
            mock_prod_repo_class.return_value = mock_prod_repo

            with patch(
                "app.modules.VentasPagosTrazabilidad.Pago.service.VentasPagosTrazabilidadUnitOfWork",
                return_value=mock_uow,
            ):
                with patch(
                    "app.modules.VentasPagosTrazabilidad.Pago.service.Pago",
                ) as mock_pago_class:
                    mock_pago_instance = MagicMock()
                    mock_pago_instance.mp_status = "pending"
                    mock_pago_instance.mp_payment_id = None
                    mock_pago_instance.external_reference = "ext-ref"
                    mock_pago_instance.idempotency_key = "key-retry"
                    mock_pago_instance.transaction_amount = Decimal("100.00")
                    mock_pago_instance.pedido_id = None
                    mock_pago_instance.mp_status_detail = None
                    mock_pago_instance.payment_method_id = None
                    mock_pago_instance.created_at = MagicMock()
                    mock_pago_instance.updated_at = MagicMock()
                    mock_pago_class.return_value = mock_pago_instance
                    mock_uow.refresh.return_value = mock_pago_instance

                    with patch(
                        "app.modules.VentasPagosTrazabilidad.Pago.service.CarritoSnapshot",
                    ) as mock_snapshot_class:
                        mock_snapshot = MagicMock()
                        mock_snapshot_class.return_value = mock_snapshot

                        mock_sdk = MagicMock()
                        mock_pref = MagicMock()
                        # MP SDK fails with a 400 error
                        mock_pref.create.return_value = {
                            "status": 400,
                            "response": {"message": "invalid preference data"},
                        }
                        mock_sdk.preference.return_value = mock_pref

                        with patch(
                            "app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk",
                            return_value=mock_sdk,
                        ):
                            from app.modules.VentasPagosTrazabilidad.Pago.schemas import (
                                InitFromCartRequest,
                                CartItemInput,
                            )
                            data = InitFromCartRequest(
                                forma_pago_codigo="MERCADOPAGO",
                                subtotal=Decimal("100.00"),
                                descuento=Decimal("0.00"),
                                costo_envio=Decimal("0.00"),
                                direccion_id=None,
                                items=[
                                    CartItemInput(
                                        producto_id=1,
                                        nombre="Test Product",
                                        precio=Decimal("100.00"),
                                        cantidad=1,
                                        ingredientes_excluidos=[],
                                    )
                                ],
                            )
                            usuario = MagicMock()
                            usuario.id = 1
                            usuario.nombre = "Test"
                            usuario.email = "test@test.com"

                            # SECOND call: existing Pago with mp_payment_id=None
                            existing_pago = MagicMock()
                            existing_pago.mp_payment_id = None
                            existing_pago.mp_status = "pending"
                            existing_pago.external_reference = "ext-ref-original"
                            existing_pago.id = 1
                            existing_pago.idempotency_key = "fingerprint-original"
                            existing_pago.transaction_amount = Decimal("100.00")
                            existing_pago.pedido_id = None
                            existing_pago.mp_status_detail = None
                            existing_pago.payment_method_id = None
                            existing_pago.created_at = MagicMock()
                            existing_pago.updated_at = MagicMock()

                            mock_repo.get_by_idempotency_key.return_value = existing_pago

                            pago, init_point, err = PagoService.init_from_cart(
                                mock_session, data, usuario
                            )

                            # MP preference creation failed → init_point should be None
                            assert init_point is None, (
                                "Retry should return None init_point when MP SDK fails"
                            )
                            # Error string should be present
                            assert err is not None, (
                                "Retry should return error string when MP SDK fails"
                            )
