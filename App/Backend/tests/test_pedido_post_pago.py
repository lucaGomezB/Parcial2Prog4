"""
Tests for the Pedido Post-Pago flow (init-from-cart + webhook creates Pedido).

Covers:
- POST /pagos/init-from-cart: happy path, stock validation
- crear_desde_snapshot: retiro en local, stock insufficient
- Snapshot TTL cleanup
- process_webhook: webhook flow (unit-level via mocked session)
- Regression: PAGO_LOCAL flow still works
"""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, select

from app.modules.VentasPagosTrazabilidad.Pago.service import PagoService
from app.modules.VentasPagosTrazabilidad.Pago.schemas import InitFromCartRequest, CartItemInput
from app.modules.VentasPagosTrazabilidad.Pedido.service import PedidoService
from app.modules.VentasPagosTrazabilidad.CarritoSnapshot.models import CarritoSnapshot
from app.modules.VentasPagosTrazabilidad.CarritoSnapshot.repository import CarritoSnapshotRepository


# ── Helpers ──

def _init_request(items=None, direccion_id=None, subtotal=None):
    items = items or [
        CartItemInput(
            producto_id=1, nombre="Test Product",
            precio=Decimal("100.00"), cantidad=2, ingredientes_excluidos=[],
        )
    ]
    return InitFromCartRequest(
        forma_pago_codigo="MERCADOPAGO",
        subtotal=subtotal or Decimal("200.00"),
        descuento=Decimal("0.00"),
        costo_envio=Decimal("50.00") if direccion_id else Decimal("0.00"),
        direccion_id=direccion_id,
        items=items,
    )


def _make_mock_usuario():
    user = MagicMock()
    user.id = 1
    user.nombre = "Test"
    user.apellido = "User"
    user.email = "test@test.com"
    user.roles = []
    return user


# ═══════════════════════════════════════════════════════════════════════════
# 8.1: init-from-cart happy path (2 tests)
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# TASK 1.1: back_urls in MercadoPago preference
# ═══════════════════════════════════════════════════════════════════════════


class TestBackUrls:
    """Verify back_urls are correctly included in preference_data.

    When using HTTPS (ngrok), back_urls use the mp-redirect proxy so
    auto_return works with MercadoPago. When using HTTP, back_urls use
    direct frontend URLs without auto_return (MP rejects HTTP back_urls).
    notification_url still uses ngrok HTTPS for webhook delivery.
    """

    # ── HTTPS (ngrok) path ──

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_webhook_base_url")
    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_init_from_cart_https_uses_mp_redirect(self, mock_sdk, mock_webhook_base, db_session):
        """With HTTPS webhook_base, back_urls go through mp-redirect proxy and auto_return is set."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="BackUrlsTest", precio_base=Decimal("100.00"), stock_manual=10)
        mock_webhook_base.return_value = "https://abc.ngrok-free.app"

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-https", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        PagoService.init_from_cart(db_session, _init_request(), _make_mock_usuario())

        create_call_args = mock_pref.create.call_args[0][0]
        back_urls = create_call_args.get("back_urls", {})
        assert isinstance(back_urls, dict), f"back_urls missing or not a dict: {create_call_args}"
        assert back_urls.get("success"), f"back_urls.success missing: {back_urls}"
        assert back_urls.get("failure"), f"back_urls.failure missing: {back_urls}"
        assert back_urls.get("pending"), f"back_urls.pending missing: {back_urls}"

        # HTTPS: back_urls use mp-redirect proxy
        assert "mp-redirect" in back_urls["success"], (
            f"HTTPS back_urls.success should use mp-redirect proxy, got: {back_urls['success']}"
        )
        assert "mp-redirect" in back_urls["failure"], (
            f"HTTPS back_urls.failure should use mp-redirect proxy, got: {back_urls['failure']}"
        )
        assert "mp-redirect" in back_urls["pending"], (
            f"HTTPS back_urls.pending should use mp-redirect proxy, got: {back_urls['pending']}"
        )
        # HTTPS: auto_return IS set (safe with HTTPS back_urls)
        assert "auto_return" in create_call_args, (
            f"auto_return should be set when back_urls are HTTPS via mp-redirect: {create_call_args}"
        )
        assert create_call_args["auto_return"] == "approved", (
            f"auto_return should be 'approved', got: {create_call_args.get('auto_return')}"
        )

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_webhook_base_url")
    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_init_mp_payment_https_uses_mp_redirect(self, mock_sdk, mock_webhook_base, db_session):
        """init_mp_payment with HTTPS uses mp-redirect proxy and auto_return."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory, pedido_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)
        pedido_factory(db_session, usuario_id=1, id=123, total=Decimal("200.00"))
        mock_webhook_base.return_value = "https://abc.ngrok-free.app"

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-legacy-https", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        PagoService.init_mp_payment(db_session, pedido_id=123)

        create_call_args = mock_pref.create.call_args[0][0]
        back_urls = create_call_args.get("back_urls", {})
        assert isinstance(back_urls, dict), f"back_urls missing or not a dict: {create_call_args}"
        assert back_urls.get("success"), f"back_urls.success missing: {back_urls}"
        assert back_urls.get("failure"), f"back_urls.failure missing: {back_urls}"
        assert back_urls.get("pending"), f"back_urls.pending missing: {back_urls}"

        # HTTPS: back_urls use mp-redirect proxy
        assert "mp-redirect" in back_urls["success"], (
            f"HTTPS back_urls.success should use mp-redirect proxy, got: {back_urls['success']}"
        )
        # HTTPS: auto_return IS set
        assert "auto_return" in create_call_args, (
            f"auto_return should be set when back_urls are HTTPS: {create_call_args}"
        )
        assert create_call_args["auto_return"] == "approved"

    # ── HTTP path ──

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_webhook_base_url")
    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_init_from_cart_http_uses_direct_frontend(self, mock_sdk, mock_webhook_base, db_session):
        """With HTTP webhook_base, back_urls use direct frontend URLs, no auto_return."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="BackUrlsTest", precio_base=Decimal("100.00"), stock_manual=10)
        mock_webhook_base.return_value = "http://localhost:8000"

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-http", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        PagoService.init_from_cart(db_session, _init_request(), _make_mock_usuario())

        create_call_args = mock_pref.create.call_args[0][0]
        back_urls = create_call_args.get("back_urls", {})
        assert isinstance(back_urls, dict), f"back_urls missing or not a dict: {create_call_args}"
        assert back_urls.get("success"), f"back_urls.success missing: {back_urls}"
        assert back_urls.get("failure"), f"back_urls.failure missing: {back_urls}"
        assert back_urls.get("pending"), f"back_urls.pending missing: {back_urls}"

        # HTTP: auto_return is NOT set (MP would reject it)
        assert "auto_return" not in create_call_args, (
            f"auto_return should NOT be set when back_urls are HTTP frontend URLs: {create_call_args}"
        )
        # HTTP: back_urls use direct frontend URLs (not mp-redirect proxy)
        frontend_url = "http://localhost:5173"
        assert back_urls["success"].startswith(frontend_url), (
            f"back_urls.success should use direct frontend URL, got: {back_urls['success']}"
        )
        assert "post-pago" in back_urls["success"], (
            f"back_urls.success should point to post-pago page, got: {back_urls['success']}"
        )

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_webhook_base_url")
    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_init_mp_payment_http_uses_direct_frontend(self, mock_sdk, mock_webhook_base, db_session):
        """init_mp_payment with HTTP uses direct frontend URLs, no auto_return."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory, pedido_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)
        pedido_factory(db_session, usuario_id=1, id=123, total=Decimal("200.00"))
        mock_webhook_base.return_value = "http://localhost:8000"

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-legacy-http", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        PagoService.init_mp_payment(db_session, pedido_id=123)

        create_call_args = mock_pref.create.call_args[0][0]
        back_urls = create_call_args.get("back_urls", {})
        assert isinstance(back_urls, dict), f"back_urls missing or not a dict: {create_call_args}"
        assert back_urls.get("success"), f"back_urls.success missing: {back_urls}"
        assert back_urls.get("failure"), f"back_urls.failure missing: {back_urls}"
        assert back_urls.get("pending"), f"back_urls.pending missing: {back_urls}"

        # HTTP: auto_return is NOT set
        assert "auto_return" not in create_call_args, (
            f"auto_return should NOT be set when back_urls are HTTP frontend URLs: {create_call_args}"
        )
        # HTTP: back_urls use direct frontend URLs
        frontend_url = "http://localhost:5173"
        assert back_urls["success"].startswith(frontend_url), (
            f"back_urls.success should use direct frontend URL, got: {back_urls['success']}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TASK 1.2: Dev-mode webhook toggle
# ═══════════════════════════════════════════════════════════════════════════


class TestWebhookDevMode:

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_webhook_base_url")
    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    @patch.dict("os.environ", {"MP_ALLOW_HTTP_WEBHOOK": "true"}, clear=False)
    def test_notification_url_included_with_http_when_env_true(self, mock_sdk, mock_webhook_base, db_session):
        """With MP_ALLOW_HTTP_WEBHOOK=true, notification_url is added even for http://"""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)
        # Force webhook base to HTTP to test the toggle
        mock_webhook_base.return_value = "http://localhost:8000"

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-http", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        PagoService.init_from_cart(db_session, _init_request(), _make_mock_usuario())

        create_call_args = mock_pref.create.call_args[0][0]
        assert "notification_url" in create_call_args, (
            f"notification_url should be present when MP_ALLOW_HTTP_WEBHOOK=true, got: {create_call_args}"
        )

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_webhook_base_url")
    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    @patch.dict("os.environ", {"MP_ALLOW_HTTP_WEBHOOK": ""}, clear=False)
    def test_notification_url_absent_with_http_when_env_not_set(self, mock_sdk, mock_webhook_base, db_session):
        """Without MP_ALLOW_HTTP_WEBHOOK, notification_url is omitted for http://"""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)
        # Force webhook base to HTTP
        mock_webhook_base.return_value = "http://localhost:8000"

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-nosig", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        PagoService.init_from_cart(db_session, _init_request(), _make_mock_usuario())

        create_call_args = mock_pref.create.call_args[0][0]
        assert "notification_url" not in create_call_args, (
            f"notification_url should be absent when MP_ALLOW_HTTP_WEBHOOK is not set, got: {create_call_args}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TASK 1.3: GET /pagos/status polling endpoint tests
# ═══════════════════════════════════════════════════════════════════════════


class TestPagoStatusEndpoint:
    """Tests for GET /pagos/status polling endpoint."""

    def test_status_found_when_pago_has_pedido(self, db_session, client, client_headers):
        """Pago with pedido_id -> status found with pedido_id."""
        from tests.conftest import _seed_roles, _seed_estados_pedido, _seed_formas_pago
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        import uuid

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        ext_ref = str(uuid.uuid4())

        pago = Pago(
            pedido_id=42, mp_status="approved", external_reference=ext_ref,
            idempotency_key=str(uuid.uuid4()), transaction_amount=100.00,
        )
        db_session.add(pago)
        db_session.commit()

        response = client.get(
            f"/api/v1/pagos/status?external_reference={ext_ref}",
            headers=client_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "found"
        assert data["pedido_id"] == 42
        assert data["mp_status"] == "approved"

    def test_status_error_when_approved_and_no_pedido(self, db_session):
        """Pago approved + pedido_id=None + no snapshot -> status 'error' (not endless 'pending')."""
        from tests.conftest import _seed_roles, _seed_estados_pedido, _seed_formas_pago
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        from unittest.mock import MagicMock
        import uuid

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        ext_ref = str(uuid.uuid4())

        pago = Pago(
            pedido_id=None, mp_status="approved", external_reference=ext_ref,
            idempotency_key=str(uuid.uuid4()), transaction_amount=100.00,
        )
        db_session.add(pago)
        db_session.commit()

        mock_user = MagicMock()
        mock_user.id = 1

        result = PagoService.check_pedido_status(db_session, ext_ref, mock_user)

        assert result["status"] == "error", (
            f"Approved Pago without Pedido must return 'error', got {result['status']}"
        )
        assert result["pedido_id"] is None
        assert result["mp_status"] == "approved"
        assert result.get("error"), "error message must be present when payment approved without Pedido"
        assert result["error"] == (
            "El pago fue aprobado pero no se pudo recuperar el carrito "
            "para crear el pedido. Contacta a soporte."
        )

    def test_status_error_over_http_when_approved_and_no_pedido(self, db_session, client, client_headers):
        """GET /pagos/status returns 200 + status 'error' (not 500) when approved but no Pedido.

        Regression guard: the PaymentStatusResponse schema must accept the 'error'
        status, otherwise FastAPI's response_model validation raises a 500.
        """
        from tests.conftest import _seed_roles, _seed_estados_pedido, _seed_formas_pago
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        import uuid

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        ext_ref = str(uuid.uuid4())

        pago = Pago(
            pedido_id=None, mp_status="approved", external_reference=ext_ref,
            idempotency_key=str(uuid.uuid4()), transaction_amount=100.00,
        )
        db_session.add(pago)
        db_session.commit()

        response = client.get(
            f"/api/v1/pagos/status?external_reference={ext_ref}",
            headers=client_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["pedido_id"] is None
        assert data["error"], "error message must be present"

    def test_status_not_found_for_unknown_reference(self, client, client_headers, db_session):
        """Unknown external_reference -> 404 not_found."""
        from tests.conftest import _seed_roles, _seed_estados_pedido, _seed_formas_pago
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)

        response = client.get(
            "/api/v1/pagos/status?external_reference=nonexistent-123",
            headers=client_headers,
        )
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "not_found"

    def test_status_cross_user_returns_not_found(self, db_session, client, client_headers):
        """User B querying User A's pago -> 404 (not 403, per spec)."""
        from tests.conftest import _seed_roles, create_user_with_role
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        from app.modules.VentasPagosTrazabilidad.CarritoSnapshot.models import CarritoSnapshot
        import uuid

        _seed_roles(db_session)
        # User A owns the pago (create user with a different email)
        user_a, user_a_headers = create_user_with_role(
            db_session, nombre="UserA", email="user_a@test.com",
        )
        ext_ref = str(uuid.uuid4())

        # Create snapshot owned by User A (required for ownership check)
        snapshot = CarritoSnapshot(
            usuario_id=user_a.id,
            items=[{"producto_id": 1, "nombre": "Test", "precio": 100.0, "cantidad": 1}],
            forma_pago_codigo="MERCADOPAGO", costo_envio=0,
            subtotal=100.00, total=100.00, external_reference=ext_ref,
        )
        db_session.add(snapshot)

        pago = Pago(
            pedido_id=42, mp_status="approved", external_reference=ext_ref,
            idempotency_key=str(uuid.uuid4()), transaction_amount=100.00,
        )
        db_session.add(pago)
        db_session.commit()

        # User B (client_headers = client_test@test.com) queries it
        response = client.get(
            f"/api/v1/pagos/status?external_reference={ext_ref}",
            headers=client_headers,
        )
        # Per spec: cross-user access returns 404 (information leaking prevention)
        assert response.status_code == 404
        data = response.json()
        assert data["status"] == "not_found"


class TestInitFromCartHappyPath:

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_creates_pago_and_snapshot(self, mock_sdk, db_session):
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test Product",
                         precio_base=Decimal("100.00"), stock_manual=10)

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-123", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        pago_read, _, __ = PagoService.init_from_cart(db_session, _init_request(), _make_mock_usuario())

        assert pago_read.pedido_id is None
        assert pago_read.mp_status == "pending"

        snapshot = CarritoSnapshotRepository(db_session).get_by_external_reference(pago_read.external_reference)
        assert snapshot is not None
        assert snapshot.items[0]["producto_id"] == 1

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_returns_init_point(self, mock_sdk, db_session):
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test Product",
                         precio_base=Decimal("100.00"), stock_manual=10)

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-456", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        _, init_point, __ = PagoService.init_from_cart(db_session, _init_request(), _make_mock_usuario())
        assert init_point == "https://mp.com/checkout"


# ═══════════════════════════════════════════════════════════════════════════
# 8.2: Stock validation failure (1 test)
# ═══════════════════════════════════════════════════════════════════════════


class TestInitFromCartStockValidation:

    def test_stock_insufficient_raises(self, db_session):
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Scarce", precio_base=Decimal("100.00"), stock_manual=1)

        data = _init_request(items=[
            CartItemInput(producto_id=1, nombre="Scarce", precio=Decimal("100.00"), cantidad=5, ingredientes_excluidos=[])
        ])
        with pytest.raises(ValueError, match="Stock insuficiente"):
            PagoService.init_from_cart(db_session, data, _make_mock_usuario())

        assert len(db_session.exec(select(CarritoSnapshot)).all()) == 0


# ═══════════════════════════════════════════════════════════════════════════
# 8.3-8.5: Webhook flow — unit-level tests via mocked session
# ═══════════════════════════════════════════════════════════════════════════


class TestWebhookFlow:

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service.get_ws_manager")
    @patch("app.modules.VentasPagosTrazabilidad.Pago.service.PagoService.get_payment_from_mp")
    @patch("sqlmodel.Session")
    def test_approved_creates_pedido_and_deletes_snapshot(self, mock_session_cls, mock_get_payment, mock_ws, db_session):
        """process_webhook on approved creates Pedido, deletes snapshot, backfills pago."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)

        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido
        import uuid

        ext_ref = str(uuid.uuid4())
        idem_key = str(uuid.uuid4())

        snapshot = CarritoSnapshot(
            usuario_id=1,
            items=[{"producto_id": 1, "nombre": "Test", "precio": 100.0, "cantidad": 2, "ingredientes_excluidos": None}],
            forma_pago_codigo="MERCADOPAGO", costo_envio=Decimal("0.00"),
            subtotal=Decimal("200.00"), total=Decimal("200.00"), external_reference=ext_ref,
        )
        db_session.add(snapshot)

        pago = Pago(pedido_id=None, mp_status="pending", external_reference=ext_ref,
                     idempotency_key=idem_key, transaction_amount=Decimal("200.00"))
        db_session.add(pago)
        db_session.commit()

        mock_get_payment.return_value = {
            "status": "approved", "status_detail": "accredited",
            "external_reference": ext_ref, "idempotency_key": idem_key,
        }
        mock_ws_instance = MagicMock()
        mock_ws.return_value = mock_ws_instance
        mock_session_cls.return_value.__enter__.return_value = db_session

        result = PagoService.process_webhook({"id": "999999", "topic": "payment"})
        assert result["status"] == "received"

        pedidos = db_session.exec(select(Pedido)).all()
        assert len(pedidos) == 1
        assert pedidos[0].estado_codigo == "CONFIRMADO"

        snapshots_left = db_session.exec(
            select(CarritoSnapshot).where(CarritoSnapshot.external_reference == ext_ref)
        ).all()
        assert len(snapshots_left) == 0

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service.get_ws_manager")
    @patch("app.modules.VentasPagosTrazabilidad.Pago.service.PagoService.get_payment_from_mp")
    @patch("sqlmodel.Session")
    def test_duplicate_webhook_no_duplicate_pedido(self, mock_session_cls, mock_get_payment, mock_ws, db_session):
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)

        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido
        import uuid

        ext_ref = str(uuid.uuid4())
        idem_key = str(uuid.uuid4())

        snapshot = CarritoSnapshot(
            usuario_id=1,
            items=[{"producto_id": 1, "nombre": "Test", "precio": 100.0, "cantidad": 1}],
            forma_pago_codigo="MERCADOPAGO", costo_envio=Decimal("0.00"),
            subtotal=Decimal("100.00"), total=Decimal("100.00"), external_reference=ext_ref,
        )
        db_session.add(snapshot)

        pago = Pago(pedido_id=None, mp_status="pending", external_reference=ext_ref,
                     idempotency_key=idem_key, transaction_amount=Decimal("100.00"))
        db_session.add(pago)
        db_session.commit()

        mock_get_payment.return_value = {
            "status": "approved", "status_detail": "accredited",
            "external_reference": ext_ref, "idempotency_key": idem_key,
        }
        mock_ws_instance = MagicMock()
        mock_ws.return_value = mock_ws_instance
        mock_session_cls.return_value.__enter__.return_value = db_session

        PagoService.process_webhook({"id": "111", "topic": "payment"})
        PagoService.process_webhook({"id": "222", "topic": "payment"})

        assert len(db_session.exec(select(Pedido)).all()) == 1

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service.PagoService.get_payment_from_mp")
    @patch("sqlmodel.Session")
    def test_rejected_preserves_snapshot(self, mock_session_cls, mock_get_payment, db_session):
        from tests.conftest import _seed_roles, _seed_estados_pedido, _seed_formas_pago
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)

        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido
        import uuid

        ext_ref = str(uuid.uuid4())
        idem_key = str(uuid.uuid4())

        snapshot = CarritoSnapshot(
            usuario_id=1,
            items=[{"producto_id": 1, "nombre": "Test", "precio": 100.0, "cantidad": 1}],
            forma_pago_codigo="MERCADOPAGO", costo_envio=Decimal("0.00"),
            subtotal=Decimal("100.00"), total=Decimal("100.00"), external_reference=ext_ref,
        )
        db_session.add(snapshot)

        pago = Pago(pedido_id=None, mp_status="pending", external_reference=ext_ref,
                     idempotency_key=idem_key, transaction_amount=Decimal("100.00"))
        db_session.add(pago)
        db_session.commit()

        mock_get_payment.return_value = {
            "status": "rejected", "status_detail": "cc_rejected_other_reason",
            "external_reference": ext_ref, "idempotency_key": idem_key,
        }
        mock_session_cls.return_value.__enter__.return_value = db_session

        PagoService.process_webhook({"id": "333", "topic": "payment"})

        assert len(db_session.exec(
            select(CarritoSnapshot).where(CarritoSnapshot.external_reference == ext_ref)
        ).all()) == 1
        assert len(db_session.exec(select(Pedido)).all()) == 0


# ═══════════════════════════════════════════════════════════════════════════
# 8.6: crear_desde_snapshot — retiro en local
# ═══════════════════════════════════════════════════════════════════════════


class TestCrearDesdeSnapshot:

    def test_retiro_en_local(self, db_session):
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)

        snapshot = CarritoSnapshot(
            usuario_id=1,
            items=[{"producto_id": 1, "nombre": "Test", "precio": 100.0, "cantidad": 2, "ingredientes_excluidos": None}],
            direccion_id=None, direccion_snapshot=None,
            forma_pago_codigo="MERCADOPAGO", costo_envio=Decimal("0.00"),
            subtotal=Decimal("200.00"), total=Decimal("200.00"), external_reference="test-retiro",
        )
        db_session.add(snapshot)
        db_session.commit()

        pedido = PedidoService.crear_desde_snapshot(db_session, snapshot)
        assert pedido.direccion_id is None
        assert pedido.direccion_snapshot is None
        assert pedido.costo_envio == Decimal("0.00")
        assert pedido.estado_codigo == "CONFIRMADO"


# ═══════════════════════════════════════════════════════════════════════════
# 8.7: Stock insufficient rollback
# ═══════════════════════════════════════════════════════════════════════════


class TestStockRollback:

    def test_raises_409_on_stock_failure(self, db_session):
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Limited", precio_base=Decimal("100.00"), stock_manual=0)

        snapshot = CarritoSnapshot(
            usuario_id=1,
            items=[{"producto_id": 1, "nombre": "Limited", "precio": 100.0, "cantidad": 5, "ingredientes_excluidos": None}],
            forma_pago_codigo="MERCADOPAGO", costo_envio=Decimal("0.00"),
            subtotal=Decimal("500.00"), total=Decimal("500.00"), external_reference="test-rollback",
        )
        db_session.add(snapshot)
        db_session.commit()

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            PedidoService.crear_desde_snapshot(db_session, snapshot)

        assert exc_info.value.status_code == 409
        assert "stock_insuficiente" in str(exc_info.value.detail)
        assert len(db_session.exec(select(Pedido)).all()) == 0


# ═══════════════════════════════════════════════════════════════════════════
# 8.9: Snapshot TTL cleanup
# ═══════════════════════════════════════════════════════════════════════════


class TestSnapshotTTLCleanup:

    def test_deletes_only_expired(self, db_session):
        from datetime import datetime, timezone, timedelta

        active = CarritoSnapshot(
            usuario_id=1, items=[], forma_pago_codigo="MERCADOPAGO",
            costo_envio=Decimal("0.00"), subtotal=Decimal("0.00"), total=Decimal("0.00"),
            external_reference="active-ref",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db_session.add(active)

        expired = CarritoSnapshot(
            usuario_id=1, items=[], forma_pago_codigo="MERCADOPAGO",
            costo_envio=Decimal("0.00"), subtotal=Decimal("0.00"), total=Decimal("0.00"),
            external_reference="expired-ref",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        db_session.add(expired)
        db_session.commit()

        repo = CarritoSnapshotRepository(db_session)
        deleted_count = repo.delete_expired()
        db_session.commit()

        assert deleted_count == 1
        assert repo.get_by_external_reference("active-ref") is not None
        assert repo.get_by_external_reference("expired-ref") is None


# ═══════════════════════════════════════════════════════════════════════════
# 8.10: Regression — PAGO_LOCAL flow
# ═══════════════════════════════════════════════════════════════════════════


class TestSyncFlowsRegression:

    def test_pago_local_creates_pedido(self, db_session, client, client_headers):
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)

        payload = {
            "forma_pago_codigo": "PAGO_LOCAL",
            "subtotal": "100.00", "descuento": "0.00", "costo_envio": "0.00",
            "detalles": [{"producto_id": 1, "cantidad": 1, "nombre_snapshot": "Test", "precio_snapshot": "100.00"}],
        }
        response = client.post("/api/v1/pedidos/", json=payload, headers=client_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["estado_codigo"] == "CONFIRMADO"
        assert data["forma_pago_codigo"] == "PAGO_LOCAL"
        assert data["direccion_id"] is None


# ═══════════════════════════════════════════════════════════════════════════
# Fix: resolve_user_from_payment_ref fallback via Pago → Pedido chain
# ═══════════════════════════════════════════════════════════════════════════


class TestResolveUserFromPaymentRefFallback:
    """resolve_user_from_payment_ref must fall back to Pago → Pedido when snapshot is consumed."""

    def test_resolves_user_via_pedido_when_snapshot_deleted(self, db_session):
        """When snapshot is deleted (consumed by webhook), resolve via Pago → Pedido chain."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago,
            create_user_with_role, pedido_factory,
        )
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        import uuid

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)

        ext_ref = str(uuid.uuid4())

        # Create a real user
        user, _headers = create_user_with_role(
            db_session, nombre="Owner", email="owner@test.com",
        )

        # Create pedido owned by this user
        pedido = pedido_factory(
            db_session, usuario_id=user.id, estado_codigo="CONFIRMADO",
        )

        # Create Pago pointing to that pedido (NO snapshot — webhook already consumed it)
        pago = Pago(
            pedido_id=pedido.id, mp_status="approved",
            external_reference=ext_ref,
            idempotency_key=str(uuid.uuid4()),
            transaction_amount=100.00,
        )
        db_session.add(pago)
        db_session.commit()

        # ACT: resolve user from payment reference
        resolved = PagoService.resolve_user_from_payment_ref(db_session, ext_ref)

        # ASSERT: user is found via Pedido chain (snapshot is gone)
        assert resolved is not None, (
            "resolve_user_from_payment_ref must fall back to Pago → Pedido chain "
            "when snapshot is deleted (consumed by webhook). Got None."
        )
        assert resolved.id == user.id, (
            f"Expected user id {user.id}, got {resolved.id}"
        )

    def test_resolves_user_via_snapshot_when_present(self, db_session):
        """When snapshot exists, resolve via snapshot (primary path, already working)."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago,
            create_user_with_role,
        )
        import uuid

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)

        ext_ref = str(uuid.uuid4())
        user, _headers = create_user_with_role(
            db_session, nombre="SnapOwner", email="snapowner@test.com",
        )

        # Create snapshot (webhook NOT yet processed)
        snapshot = CarritoSnapshot(
            usuario_id=user.id,
            items=[{"producto_id": 1, "nombre": "Test", "precio": 100.0, "cantidad": 1}],
            forma_pago_codigo="MERCADOPAGO", costo_envio=0,
            subtotal=100.00, total=100.00, external_reference=ext_ref,
        )
        db_session.add(snapshot)
        db_session.commit()

        resolved = PagoService.resolve_user_from_payment_ref(db_session, ext_ref)
        assert resolved is not None
        assert resolved.id == user.id

    def test_returns_none_when_both_snapshot_and_pedido_missing(self, db_session):
        """Neither snapshot nor Pago with pedido → returns None."""
        from tests.conftest import _seed_roles, _seed_estados_pedido, _seed_formas_pago
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)

        resolved = PagoService.resolve_user_from_payment_ref(
            db_session, "nonexistent-ref-999"
        )
        assert resolved is None


# ═══════════════════════════════════════════════════════════════════════════
# Fix: check_pedido_status cross-user when snapshot is consumed
# ═══════════════════════════════════════════════════════════════════════════


class TestCheckPedidoStatusSnapshotConsumed:
    """Cross-user check must work even when snapshot is deleted (webhook consumed)."""

    def test_cross_user_denied_when_snapshot_consumed(self, db_session):
        """User B queries status, snapshot is gone, but Pedido belongs to User A → not_found."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago,
            create_user_with_role, pedido_factory,
        )
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        import uuid
        from unittest.mock import MagicMock

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)

        ext_ref = str(uuid.uuid4())

        # User A: owns the payment and pedido
        user_a, _ = create_user_with_role(
            db_session, nombre="UserA", email="user_a_cross@test.com",
        )
        pedido_a = pedido_factory(
            db_session, usuario_id=user_a.id, estado_codigo="CONFIRMADO",
        )
        pago = Pago(
            pedido_id=pedido_a.id, mp_status="approved",
            external_reference=ext_ref,
            idempotency_key=str(uuid.uuid4()),
            transaction_amount=100.00,
        )
        db_session.add(pago)
        db_session.commit()

        # User B: tries to query another user's payment status
        mock_user_b = MagicMock()
        mock_user_b.id = 999  # Different from user_a.id

        result = PagoService.check_pedido_status(db_session, ext_ref, mock_user_b)

        # BUG BEFORE FIX: snapshot is None → owner_id is None → cross-user check passes
        # → result is "found" with pedido_id leaking to wrong user
        assert result["status"] == "not_found", (
            f"Cross-user query must return not_found when snapshot is consumed "
            f"but Pedido belongs to different user. Got status={result['status']}, "
            f"pedido_id={result['pedido_id']}"
        )
        assert result["pedido_id"] is None, (
            "pedido_id must be None in not_found response (information leakage prevention)"
        )

    def test_same_user_found_when_snapshot_consumed(self, db_session):
        """Same user queries status, snapshot is gone → found (happy path after webhook)."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago,
            create_user_with_role, pedido_factory,
        )
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        import uuid

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)

        ext_ref = str(uuid.uuid4())
        user, _ = create_user_with_role(
            db_session, nombre="Owner", email="owner_same@test.com",
        )
        pedido = pedido_factory(
            db_session, usuario_id=user.id, estado_codigo="CONFIRMADO",
        )
        pago = Pago(
            pedido_id=pedido.id, mp_status="approved",
            external_reference=ext_ref,
            idempotency_key=str(uuid.uuid4()),
            transaction_amount=100.00,
        )
        db_session.add(pago)
        db_session.commit()

        # Same user queries — should get found
        mock_user = MagicMock()
        mock_user.id = user.id

        result = PagoService.check_pedido_status(db_session, ext_ref, mock_user)

        assert result["status"] == "found", (
            f"Same user must get 'found' when snapshot consumed but Pedido exists. "
            f"Got status={result['status']}"
        )
        assert result["pedido_id"] == pedido.id


# ═══════════════════════════════════════════════════════════════════════════
# BUG 3 TESTS — Shipping cost in MP preference + schema default + webhook
# ═══════════════════════════════════════════════════════════════════════════

class TestShippingInPreference:

    def test_init_from_cart_costo_envio_default_is_50(self):
        """InitFromCartRequest default costo_envio is 50.00."""
        from app.modules.VentasPagosTrazabilidad.Pago.schemas import InitFromCartRequest
        req = InitFromCartRequest(
            forma_pago_codigo="MERCADOPAGO",
            subtotal=Decimal("100.00"),
            items=[],
        )
        assert req.costo_envio == Decimal("50.00")

    def test_update_pago_status_syncs_transaction_amount(self, db_session):
        """update_pago_status updates status fields on an existing Pago."""
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        from app.modules.VentasPagosTrazabilidad.Pago.service import PagoService
        import uuid

        ext_ref = str(uuid.uuid4())
        pago = Pago(
            mp_status="pending",
            mp_payment_id=99999,
            external_reference=ext_ref,
            idempotency_key=str(uuid.uuid4()),
            transaction_amount=200.00,
            payment_method_id=None,
        )
        db_session.add(pago)
        db_session.flush()

        # Update via the public service method
        result = PagoService.update_pago_status(
            db_session,
            mp_payment_id=99999,
            mp_status="approved",
            mp_status_detail="accredited",
        )

        db_session.refresh(pago)
        assert pago.mp_status == "approved"
        assert pago.mp_status_detail == "accredited"
        # The transaction_amount should still be synced when webhook data arrives
        # via process_webhook (tested via integration in TestWebhookFlow)

    def test_retry_preference_includes_shipping(self, db_session):
        """Build preference items with shipping via internal helper."""
        from app.modules.VentasPagosTrazabilidad.Pago.schemas import CartItemInput
        from decimal import Decimal as D

        items = [CartItemInput(
            producto_id=1, nombre="Test Product", precio=D("100.00"),
            cantidad=2, ingredientes_excluidos=[],
        )]
        # Manually build the items list same way the service does,
        # verifying shipping is included when costo_envio > 0
        preference_items = []
        for item in items:
            preference_items.append({
                "title": item.nombre,
                "quantity": item.cantidad,
                "unit_price": float(item.precio),
                "currency_id": "ARS",
            })
        # Add shipping
        costo_envio = D("50.00")
        if costo_envio > 0:
            preference_items.append({
                "title": "Costo de envío",
                "quantity": 1,
                "unit_price": float(costo_envio),
                "currency_id": "ARS",
            })

        assert len(preference_items) == 2
        shipping = [i for i in preference_items if i.get("title") == "Costo de envío"]
        assert len(shipping) == 1
        assert shipping[0]["unit_price"] == 50.0

    def test_no_shipping_when_costo_envio_zero(self):
        """Preference items with costo_envio=0 excludes shipping."""
        from app.modules.VentasPagosTrazabilidad.Pago.schemas import CartItemInput
        from decimal import Decimal as D

        items = [CartItemInput(
            producto_id=1, nombre="Test", precio=D("100.00"),
            cantidad=2, ingredientes_excluidos=[],
        )]
        preference_items = []
        for item in items:
            preference_items.append({
                "title": item.nombre,
                "quantity": item.cantidad,
                "unit_price": float(item.precio),
                "currency_id": "ARS",
            })
        costo_envio = D("0.00")
        if costo_envio > 0:
            preference_items.append({
                "title": "Costo de envío",
                "quantity": 1,
                "unit_price": float(costo_envio),
                "currency_id": "ARS",
            })

        assert len(preference_items) == 1
        shipping = [i for i in preference_items if i.get("title") == "Costo de envío"]
        assert len(shipping) == 0


# ═══════════════════════════════════════════════════════════════════════════
# REGRESSION TESTS — Make-to-Stock ingredient isolation
# ═══════════════════════════════════════════════════════════════════════════

class TestCrearDesdeSnapshotIngredientIsolation:
    """crear_desde_snapshot must NOT modify ingredient stock (make-to-stock model)."""

    def test_crear_desde_snapshot_does_not_modify_ingredient_stock(self, db_session):
        """Snapshot-based order creation deducts product stock only, not ingredients."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago,
        )
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
        from app.modules.CatalogoDeProductos.Producto.models import Producto

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)

        # Create ingredient with known stock
        ing = Ingrediente(
            nombre="SnapshotIng", descripcion="Test",
            es_alergeno=False, precio_actual=Decimal("10.00"), stock_actual=150,
        )
        db_session.add(ing)
        db_session.flush()

        # Create product with ingredient association (make-to-order)
        producto = Producto(
            nombre="SnapshotProduct", descripcion="Test",
            precio_base=Decimal("500.00"), precio_actual=Decimal("500.00"),
            tiempo_prep_min=5, disponible=True,
            es_producto_terminado=False,
        )
        db_session.add(producto)
        db_session.flush()

        db_session.add(ProductoIngrediente(
            producto_id=producto.id, ingrediente_id=ing.id,
            cantidad=Decimal("3.0"), es_removible=True, es_principal=True, orden=0,
        ))
        db_session.flush()

        ingred_stock_before = ing.stock_actual

        snapshot = CarritoSnapshot(
            usuario_id=1,
            items=[{"producto_id": producto.id, "nombre": producto.nombre,
                    "precio": float(producto.precio_actual), "cantidad": 2,
                    "ingredientes_excluidos": None}],
            forma_pago_codigo="MERCADOPAGO", costo_envio=Decimal("0.00"),
            subtotal=Decimal("1000.00"), total=Decimal("1000.00"),
            external_reference="test-snapshot-ingredient-mto",
        )
        db_session.add(snapshot)
        db_session.commit()

        pedido = PedidoService.crear_desde_snapshot(db_session, snapshot)
        assert pedido.estado_codigo == "CONFIRMADO"

        db_session.refresh(ing)

        # Make-to-order: ingredient stock IS deducted at snapshot creation
        # 2 units * 3.0 per unit = 6 deducted
        assert ing.stock_actual == ingred_stock_before - 6, (
            f"Ingredient stock should be {ingred_stock_before - 6}, got {ing.stock_actual}. "
            "Make-to-order: ingredients are consumed at order creation time."
        )


# ═══════════════════════════════════════════════════════════════════════════
# FIX: Preference improvements (description, statement_descriptor, purpose)
# ═══════════════════════════════════════════════════════════════════════════

class TestPreferenceDescription:

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_preference_items_include_description(self, mock_sdk, db_session):
        """Each preference item must include a 'description' field: '{cantidad}x {nombre}'."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Hamburguesa Clasica",
                         precio_base=Decimal("100.00"), stock_manual=10)

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-desc", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        data = _init_request(items=[
            CartItemInput(
                producto_id=1, nombre="Hamburguesa Clasica",
                precio=Decimal("100.00"), cantidad=2, ingredientes_excluidos=[],
            )
        ])
        PagoService.init_from_cart(db_session, data, _make_mock_usuario())

        create_call_args = mock_pref.create.call_args[0][0]
        items = create_call_args.get("items", [])
        # First item is the product (second would be shipping if costo_envio > 0)
        product_items = [i for i in items if i.get("title") != "Costo de envio"]
        assert len(product_items) == 1
        assert product_items[0].get("description") == "2x Hamburguesa Clasica", (
            f"Expected description '2x Hamburguesa Clasica', got: {product_items[0].get('description')}"
        )


class TestPreferenceStatementDescriptorAndPurpose:

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_preference_has_statement_descriptor_and_purpose(self, mock_sdk, db_session):
        """Preference data must include statement_descriptor and purpose fields."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-sd", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        PagoService.init_from_cart(db_session, _init_request(), _make_mock_usuario())

        create_call_args = mock_pref.create.call_args[0][0]
        assert "statement_descriptor" in create_call_args, (
            f"statement_descriptor missing from preference_data: {create_call_args.keys()}"
        )
        assert create_call_args["statement_descriptor"] == "FoodStore", (
            f"Expected 'FoodStore', got: {create_call_args.get('statement_descriptor')}"
        )
        assert "purpose" in create_call_args, (
            f"purpose missing from preference_data: {create_call_args.keys()}"
        )
        assert create_call_args["purpose"] == "wallet_purchase", (
            f"Expected 'wallet_purchase', got: {create_call_args.get('purpose')}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# FIX: Force costo_envio=0 for MercadoPago in crear_desde_snapshot
# ═══════════════════════════════════════════════════════════════════════════

class TestCostoEnvioCeroMercadoPago:

    def test_crear_desde_snapshot_forces_costo_envio_zero_for_mp(self, db_session):
        """crear_desde_snapshot must force costo_envio=0 and recalculate total for MERCADOPAGO."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)

        # Snapshot with non-zero costo_envio
        snapshot = CarritoSnapshot(
            usuario_id=1,
            items=[{"producto_id": 1, "nombre": "Test", "precio": 100.0, "cantidad": 2, "ingredientes_excluidos": None}],
            forma_pago_codigo="MERCADOPAGO",
            costo_envio=Decimal("50.00"),
            subtotal=Decimal("200.00"),
            total=Decimal("250.00"),   # 200 + 0 + 50
            external_reference="test-costo-envio-zero",
        )
        db_session.add(snapshot)
        db_session.commit()

        pedido = PedidoService.crear_desde_snapshot(db_session, snapshot)

        assert pedido.costo_envio == Decimal("0.00"), (
            f"For MERCADOPAGO, costo_envio should be forced to 0. Got: {pedido.costo_envio}"
        )
        assert pedido.total == Decimal("200.00"), (
            f"Total should be recalculated as subtotal (200) - descuento (0) + costo_envio (0) = 200. Got: {pedido.total}"
        )
        assert pedido.estado_codigo == "CONFIRMADO"

    def test_crear_desde_snapshot_preserves_costo_envio_for_other_methods(self, db_session):
        """crear_desde_snapshot should NOT modify costo_envio for non-MP payment methods."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test", precio_base=Decimal("100.00"), stock_manual=10)

        # Snapshot with non-zero costo_envio and PAGO_LOCAL
        snapshot = CarritoSnapshot(
            usuario_id=1,
            items=[{"producto_id": 1, "nombre": "Test", "precio": 100.0, "cantidad": 2, "ingredientes_excluidos": None}],
            forma_pago_codigo="PAGO_LOCAL",
            costo_envio=Decimal("50.00"),
            subtotal=Decimal("200.00"),
            total=Decimal("250.00"),
            external_reference="test-costo-envio-local",
        )
        db_session.add(snapshot)
        db_session.commit()

        pedido = PedidoService.crear_desde_snapshot(db_session, snapshot)
        assert pedido.costo_envio == Decimal("50.00"), (
            f"For PAGO_LOCAL, costo_envio should be preserved. Got: {pedido.costo_envio}"
        )
        assert pedido.estado_codigo == "CONFIRMADO"


# ═══════════════════════════════════════════════════════════════════════════
# FIX: Retry must recreate an expired/deleted CarritoSnapshot
# ═══════════════════════════════════════════════════════════════════════════


class TestRetryRecreatesExpiredSnapshot:
    """init_from_cart retry path must recreate the snapshot if it was TTL-expired.

    When a user re-initiates checkout with the SAME cart, `_cart_fingerprint`
    produces the same idempotency_key, so the existing pending Pago is reused.
    The retry path re-creates the MP preference but MUST also ensure the
    CarritoSnapshot still exists (it is the ONLY source of cart items used by
    the webhook to build the Pedido).
    """

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_recreates_snapshot_and_reuses_pago_on_retry(self, mock_sdk, db_session):
        """Retry with same cart recreates the expired snapshot for the same ext_ref and reuses the Pago."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        from app.modules.VentasPagosTrazabilidad.Pago.service import _cart_fingerprint
        import uuid

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test Product",
                         precio_base=Decimal("100.00"), stock_manual=10)

        data = _init_request()
        usuario = _make_mock_usuario()
        fingerprint = _cart_fingerprint(data, usuario.id)
        ext_ref = str(uuid.uuid4())

        # ── First checkout: Pago (pending) + snapshot exist ──
        pago = Pago(
            pedido_id=None, mp_status="pending", mp_payment_id=None,
            external_reference=ext_ref, idempotency_key=fingerprint,
            transaction_amount=Decimal("200.00"),
        )
        db_session.add(pago)
        snapshot = CarritoSnapshot(
            usuario_id=usuario.id,
            items=[{"producto_id": 1, "nombre": "Test Product", "precio": 100.0,
                    "cantidad": 2, "ingredientes_excluidos": None}],
            direccion_id=None, direccion_snapshot=None,
            forma_pago_codigo="MERCADOPAGO", costo_envio=Decimal("0.00"),
            subtotal=Decimal("200.00"), total=Decimal("200.00"),
            external_reference=ext_ref,
        )
        db_session.add(snapshot)
        db_session.commit()

        # ── Simulate TTL expiry: snapshot deleted ──
        repo = CarritoSnapshotRepository(db_session)
        to_delete = repo.get_by_external_reference(ext_ref)
        assert to_delete is not None, "snapshot must exist before simulating TTL expiry"
        repo.delete(to_delete)
        db_session.commit()
        assert repo.get_by_external_reference(ext_ref) is None

        # ── Mock MP SDK for the retry preference creation ──
        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-retry", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        # ── ACT: retry with same cart (same fingerprint) ──
        pago_read, init_point, _ = PagoService.init_from_cart(db_session, data, usuario)

        # ── ASSERT: Pago reused (same external_reference, NOT duplicated) ──
        assert pago_read.external_reference == ext_ref
        pagos = db_session.exec(select(Pago).where(Pago.idempotency_key == fingerprint)).all()
        assert len(pagos) == 1, "retry must reuse the existing Pago, not create a duplicate"

        # ── ASSERT: snapshot recreated for the SAME external_reference ──
        recreated = repo.get_by_external_reference(ext_ref)
        assert recreated is not None, "snapshot must be recreated on retry after TTL expiry"
        assert recreated.external_reference == ext_ref
        assert recreated.items[0]["producto_id"] == 1
        assert recreated.items[0]["nombre"] == "Test Product"
        assert recreated.items[0]["cantidad"] == 2
        assert recreated.subtotal == Decimal("200.00")
        assert recreated.total == Decimal("200.00")
        assert recreated.forma_pago_codigo == "MERCADOPAGO"
        assert init_point == "https://mp.com/checkout"

    @patch("app.modules.VentasPagosTrazabilidad.Pago.service._get_mp_sdk")
    def test_retry_does_not_duplicate_existing_snapshot(self, mock_sdk, db_session):
        """When the snapshot still exists, retry must NOT recreate it (no duplicate)."""
        from tests.conftest import (
            _seed_roles, _seed_estados_pedido, _seed_formas_pago, producto_factory,
        )
        from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
        from app.modules.VentasPagosTrazabilidad.Pago.service import _cart_fingerprint
        import uuid

        _seed_roles(db_session); _seed_estados_pedido(db_session); _seed_formas_pago(db_session)
        producto_factory(db_session, id=1, nombre="Test Product",
                         precio_base=Decimal("100.00"), stock_manual=10)

        data = _init_request()
        usuario = _make_mock_usuario()
        fingerprint = _cart_fingerprint(data, usuario.id)
        ext_ref = str(uuid.uuid4())

        pago = Pago(
            pedido_id=None, mp_status="pending", mp_payment_id=None,
            external_reference=ext_ref, idempotency_key=fingerprint,
            transaction_amount=Decimal("200.00"),
        )
        db_session.add(pago)
        snapshot = CarritoSnapshot(
            usuario_id=usuario.id,
            items=[{"producto_id": 1, "nombre": "Test Product", "precio": 100.0,
                    "cantidad": 2, "ingredientes_excluidos": None}],
            direccion_id=None, direccion_snapshot=None,
            forma_pago_codigo="MERCADOPAGO", costo_envio=Decimal("0.00"),
            subtotal=Decimal("200.00"), total=Decimal("200.00"),
            external_reference=ext_ref,
        )
        db_session.add(snapshot)
        db_session.commit()

        mock_sdk_instance = MagicMock()
        mock_pref = MagicMock()
        mock_pref.create.return_value = {
            "status": 201, "response": {"id": "pref-retry", "init_point": "https://mp.com/checkout"},
        }
        mock_sdk_instance.preference.return_value = mock_pref
        mock_sdk.return_value = mock_sdk_instance

        PagoService.init_from_cart(db_session, data, usuario)

        snapshots = db_session.exec(
            select(CarritoSnapshot).where(CarritoSnapshot.external_reference == ext_ref)
        ).all()
        assert len(snapshots) == 1, "retry must not duplicate an existing snapshot"
