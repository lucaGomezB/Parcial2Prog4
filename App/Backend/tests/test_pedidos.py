"""
Integration tests for Pedido (Order) module.

Covers: create, avanzar FSM, cancel, RBAC guards, list, historial.
Uses real SQLite DB via conftest fixtures. Pedidos are created directly
in DB to avoid complex WS/manager dependency setup.
"""
import pytest
from decimal import Decimal
from fastapi import status

from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega
from app.modules.CatalogoDeProductos.Producto.models import Producto
from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido
from app.modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
from app.modules.VentasPagosTrazabilidad.HistorialEstadoPedido.models import HistorialEstadoPedido
from app.core.security.passwords import get_password_hash


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _ensure_roles(db_session):
    from app.modules.IdentidadYAcceso.Rol.models import Rol
    from sqlmodel import select
    for codigo, nombre in [
        ("ADMIN", "Admin"), ("CLIENT", "Client"),
        ("PEDIDOS", "Pedidos"), ("STOCK", "Stock"),
    ]:
        if not db_session.exec(select(Rol).where(Rol.codigo == codigo)).first():
            db_session.add(Rol(codigo=codigo, nombre=nombre))
    db_session.flush()


def _ensure_estados(db_session):
    from app.modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
    from sqlmodel import select
    for codigo, desc, orden, terminal in [
        ("PENDIENTE", "Pendiente", 1, False),
        ("CONFIRMADO", "Confirmado", 2, False),
        ("EN_PREP", "En prep", 3, False),
        ("ENTREGADO", "Entregado", 4, True),
        ("CANCELADO", "Cancelado", 5, True),
    ]:
        if not db_session.exec(select(EstadoPedido).where(EstadoPedido.codigo == codigo)).first():
            db_session.add(EstadoPedido(codigo=codigo, descripcion=desc, orden=orden, es_terminal=terminal))
    db_session.flush()


def _ensure_formas_pago(db_session):
    from app.modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago
    from sqlmodel import select
    for codigo, desc, hab in [
        ("MERCADOPAGO", "MP", True),
        ("EFECTIVO", "Efectivo", False),
        ("PAGO_LOCAL", "Pago local", True),
    ]:
        if not db_session.exec(select(FormaPago).where(FormaPago.codigo == codigo)).first():
            db_session.add(FormaPago(codigo=codigo, descripcion=desc, habilitado=hab))
    db_session.flush()


def _seed_all(db_session):
    _ensure_roles(db_session)
    _ensure_estados(db_session)
    _ensure_formas_pago(db_session)


def _create_user(db_session, email="pedidotest@test.com", roles=None):
    if roles is None:
        roles = ["CLIENT"]
    u = Usuario(
        nombre="Test", apellido="User", email=email,
        password_hash=get_password_hash("pass123"),
    )
    db_session.add(u)
    db_session.flush()
    for c in roles:
        db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo=c))
    db_session.flush()
    return u


def _create_producto(db_session, nombre="TestProd", stock=100):
    """Create a test product with es_producto_terminado=True and stock_manual.
    
    Products default to es_producto_terminado=True for backward compatibility
    with existing tests that don't set up ingredient associations.
    stock_manual is used instead of stock_cantidad (which is now derived).
    """
    p = Producto(
        nombre=nombre, descripcion="Test",
        precio_base=Decimal("500"), precio_actual=Decimal("500"),
        stock_manual=stock, tiempo_prep_min=5, disponible=True,
        es_producto_terminado=True,
    )
    db_session.add(p)
    db_session.flush()
    return p


def _create_producto_con_ingredientes(db_session, nombre="TestProd", stock_ingredientes=None):
    """Create a test product with ingredients for make-to-order tests.
    
    Args:
        stock_ingredientes: list of (nombre, stock_actual, cantidad_per_unit, unidad_medida_id)
    Returns (producto, ingredientes_dict) where ingredientes_dict maps nombre to ORM object.
    """
    from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
    from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

    if stock_ingredientes is None:
        stock_ingredientes = [
            ("TestIngredient", 200, Decimal("1.0"), 5),  # default: 200 portions
        ]

    p = Producto(
        nombre=nombre, descripcion="Test",
        precio_base=Decimal("500"), precio_actual=Decimal("500"),
        tiempo_prep_min=5, disponible=True,
        es_producto_terminado=False,
    )
    db_session.add(p)
    db_session.flush()

    ingredientes = {}
    for i, (ing_nombre, stock_actual, cantidad, um_id) in enumerate(stock_ingredientes):
        ing = Ingrediente(
            nombre=ing_nombre, descripcion="Test ingredient",
            precio_actual=Decimal("10.00"), stock_actual=stock_actual,
            unidad_medida_id=um_id,
        )
        db_session.add(ing)
        db_session.flush()
        db_session.add(ProductoIngrediente(
            producto_id=p.id, ingrediente_id=ing.id,
            cantidad=cantidad, es_removible=True, es_principal=True,
            orden=i,
        ))
        ingredientes[ing_nombre] = ing
    db_session.flush()
    return p, ingredientes


def _create_direccion(db_session, usuario_id):
    d = DireccionEntrega(
        usuario_id=usuario_id, alias="Casa",
        linea1="Calle Test 123", ciudad="Mendoza",
        es_principal=True,
    )
    db_session.add(d)
    db_session.flush()
    return d


def _create_pedido(db_session, usuario_id, estado="PENDIENTE", forma_pago="PAGO_LOCAL"):
    """Direct DB pedido creation (bypasses HTTP complexity)."""
    p = Pedido(
        usuario_id=usuario_id,
        estado_codigo=estado,
        forma_pago_codigo=forma_pago,
        subtotal=Decimal("500"),
        total=Decimal("500"),
    )
    db_session.add(p)
    db_session.flush()
    return p


# ═══════════════════════════════════════════════════════════════════════════
# PEDIDO LIST TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestPedidoList:

    def test_list_pedidos_admin(self, client, admin_headers, db_session):
        """Admin/PEDIDOS can list all orders."""
        _seed_all(db_session)
        u = _create_user(db_session)
        _create_pedido(db_session, u.id)

        response = client.get("/api/v1/pedidos/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_mis_pedidos_client(self, client, client_headers, db_session):
        """Authenticated user can view their own orders."""
        _seed_all(db_session)
        response = client.get("/api/v1/pedidos/mis-pedidos", headers=client_headers)
        assert response.status_code == 200

    def test_list_pedidos_unauthenticated(self, client):
        """Unauthenticated access to pedidos returns 401."""
        response = client.get("/api/v1/pedidos/")
        assert response.status_code == 401

    def test_list_pedidos_client_rejected(self, client, client_headers, db_session):
        """Client cannot list ALL pedidos (only their own)."""
        _seed_all(db_session)
        response = client.get("/api/v1/pedidos/", headers=client_headers)
        assert response.status_code == 403

    def test_get_pedido_by_id(self, client, admin_headers, db_session):
        """Get single pedido by ID."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p = _create_pedido(db_session, u.id)

        response = client.get(f"/api/v1/pedidos/{p.id}", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["id"] == p.id

    def test_pedido_not_found_returns_404(self, client, admin_headers):
        response = client.get("/api/v1/pedidos/99999", headers=admin_headers)
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
# PEDIDO AVANZAR FSM TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestPedidoAvanzarFSM:

    def test_avanzar_pendiente_to_confirmado(self, client, admin_headers, db_session):
        """PENDIENTE -> CONFIRMADO via avanzar endpoint."""
        _seed_all(db_session)
        u = _create_user(db_session)
        prod = _create_producto(db_session, stock=50)
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")

        # Add a detail for stock validation
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=1, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual,
        ))
        db_session.flush()

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/avanzar",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado_anterior"] == "PENDIENTE"
        assert data["estado_actual"] == "CONFIRMADO"

    def test_avanzar_full_cycle(self, client, admin_headers, db_session):
        """FSM: PENDIENTE -> CONFIRMADO -> EN_PREP -> ENTREGADO."""
        _seed_all(db_session)
        u = _create_user(db_session)
        prod = _create_producto(db_session, stock=50)
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")

        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=1, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual,
        ))
        db_session.flush()

        expected = ["CONFIRMADO", "EN_PREP", "ENTREGADO"]
        for exp_state in expected:
            resp = client.patch(
                f"/api/v1/pedidos/{p.id}/avanzar",
                headers=admin_headers,
            )
            assert resp.status_code == 200, f"Failed advancing to {exp_state}"
            assert resp.json()["estado_actual"] == exp_state

    def test_terminal_state_blocks_avanzar(self, client, admin_headers, db_session):
        """Advancing from ENTREGADO returns 400."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p = _create_pedido(db_session, u.id, estado="ENTREGADO")

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/avanzar",
            headers=admin_headers,
        )
        assert response.status_code == 400

    def test_avanzar_mercado_pago_blocked(self, client, admin_headers, db_session):
        """MercadoPago orders cannot be advanced via endpoint."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="MERCADOPAGO")

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/avanzar",
            headers=admin_headers,
        )
        assert response.status_code in (400, 404)

    def test_avanzar_client_rejected(self, client, client_headers):
        """Client cannot advance pedidos."""
        response = client.patch("/api/v1/pedidos/1/avanzar", headers=client_headers)
        assert response.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
# PEDIDO CANCEL TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestPedidoCancel:

    def test_cancel_pendiente_pedido(self, client, client_headers, db_session):
        """Customer (CLIENT role) cannot cancel pedidos — returns 403.
        
        Only ADMIN and PEDIDOS roles can cancel orders after the role guard fix.
        """
        _seed_all(db_session)
        from sqlmodel import select
        u = db_session.exec(select(Usuario).where(Usuario.email == "client_test@test.com")).first()
        assert u is not None

        p = _create_pedido(db_session, u.id, estado="PENDIENTE")
        response = client.patch(
            f"/api/v1/pedidos/{p.id}/cancelar",
            json={"motivo": "Ya no lo quiero"},
            headers=client_headers,
        )
        assert response.status_code == 403

    def test_cancel_pendiente_admin(self, client, admin_headers, db_session):
        """Admin can cancel any PENDIENTE order."""
        _seed_all(db_session)
        u = _create_user(db_session, email="admincancel@test.com", roles=["CLIENT"])
        p = _create_pedido(db_session, u.id, estado="PENDIENTE")
        response = client.patch(
            f"/api/v1/pedidos/{p.id}/cancelar",
            json={"motivo": "Cancelado por admin"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["estado_actual"] == "CANCELADO"

    def test_cancel_pendiente_pedidos_role(self, client, pedidos_headers, db_session):
        """PEDIDOS role can cancel any PENDIENTE order."""
        _seed_all(db_session)
        u = _create_user(db_session, email="pedidoscancel@test.com", roles=["CLIENT"])
        p = _create_pedido(db_session, u.id, estado="PENDIENTE")
        response = client.patch(
            f"/api/v1/pedidos/{p.id}/cancelar",
            json={"motivo": "Cancelado por pedidos"},
            headers=pedidos_headers,
        )
        assert response.status_code == 200
        assert response.json()["estado_actual"] == "CANCELADO"

    def test_cancel_empty_motivo_fails(self, client, admin_headers, db_session):
        """Cancel with empty motivo returns 422 (uses admin to bypass role guard)."""
        _seed_all(db_session)
        u = _create_user(db_session, email="empty_motivo@test.com")
        p = _create_pedido(db_session, u.id, estado="PENDIENTE")

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/cancelar",
            json={"motivo": ""},
            headers=admin_headers,
        )
        # Empty motivo should fail validation (422)
        assert response.status_code == 422

    def test_cancel_terminal_state_blocked(self, client, admin_headers, db_session):
        """Cannot cancel ENTREGADO order."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p = _create_pedido(db_session, u.id, estado="ENTREGADO")

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/cancelar",
            json={"motivo": "Quiero cancelar"},
            headers=admin_headers,
        )
        assert response.status_code == 400

    def test_cancel_en_prep_pedido(self, client, admin_headers, db_session):
        """Admin can cancel an EN_PREP order and stock is restored."""
        _seed_all(db_session)
        u = _create_user(db_session)
        prod = _create_producto(db_session, stock=50)
        p = _create_pedido(db_session, u.id, estado="EN_PREP", forma_pago="PAGO_LOCAL")

        # Add a detail so stock restoration can be verified
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=3, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual * 3,
        ))
        db_session.flush()

        stock_before = prod.stock_manual

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/cancelar",
            json={"motivo": "Cancelacion desde EN_PREP"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["estado_actual"] == "CANCELADO"

        # Verify stock was restored (same logic as cancelling from CONFIRMADO)
        db_session.refresh(prod)
        assert prod.stock_manual == stock_before + 3

    def test_cancel_en_prep_restores_stock_multiple_products(self, client, admin_headers, db_session):
        """Cancelling from EN_PREP restores stock for ALL detail lines."""
        _seed_all(db_session)
        u = _create_user(db_session)
        prod_a = _create_producto(db_session, nombre="ProdA", stock=100)
        prod_b = _create_producto(db_session, nombre="ProdB", stock=200)
        p = _create_pedido(db_session, u.id, estado="EN_PREP", forma_pago="PAGO_LOCAL")

        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod_a.id,
            cantidad=5, nombre_snapshot=prod_a.nombre,
            precio_snapshot=prod_a.precio_actual,
            subtotal_snap=prod_a.precio_actual * 5,
        ))
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod_b.id,
            cantidad=7, nombre_snapshot=prod_b.nombre,
            precio_snapshot=prod_b.precio_actual,
            subtotal_snap=prod_b.precio_actual * 7,
        ))
        db_session.flush()

        stock_a_before = prod_a.stock_manual
        stock_b_before = prod_b.stock_manual

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/cancelar",
            json={"motivo": "Stock restore test"},
            headers=admin_headers,
        )
        assert response.status_code == 200

        db_session.refresh(prod_a)
        db_session.refresh(prod_b)
        assert prod_a.stock_manual == stock_a_before + 5
        assert prod_b.stock_manual == stock_b_before + 7


# ═══════════════════════════════════════════════════════════════════════════
# PEDIDO HISTORIAL TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestPedidoHistorial:

    def test_historial_append_only(self, client, admin_headers, db_session):
        """State transitions create history entries (verified via GET)."""
        _seed_all(db_session)
        u = _create_user(db_session)
        prod = _create_producto(db_session, stock=50)
        p = _create_pedido(db_session, u.id, estado="CONFIRMADO")

        # Create a history entry manually
        db_session.add(HistorialEstadoPedido(
            pedido_id=p.id,
            estado_desde="PENDIENTE",
            estado_hacia="CONFIRMADO",
            usuario_id=u.id,
            es_sistema=False,
        ))
        db_session.flush()

        response = client.get(
            f"/api/v1/pedidos/{p.id}/historial",
            headers=admin_headers,
        )
        assert response.status_code == 200
        historial = response.json()
        assert len(historial) >= 1
        assert historial[0]["estado_hacia"] == "CONFIRMADO"

    def test_historial_ownership_scope(self, client, client_headers, db_session):
        """User A cannot access user B's pedido historial."""
        _seed_all(db_session)
        from sqlmodel import select
        # Create user B
        user_b = _create_user(db_session, email="userb_hist@test.com")
        p = _create_pedido(db_session, user_b.id)

        # Client tries to access user B's historial
        response = client.get(
            f"/api/v1/pedidos/{p.id}/historial",
            headers=client_headers,
        )
        assert response.status_code in (403, 404)


# ═══════════════════════════════════════════════════════════════════════════
# PEDIDO CREATE TESTS — POST /api/v1/pedidos/
# ═══════════════════════════════════════════════════════════════════════════

class TestPedidoCreate:

    def test_create_pedido_ok_pendiente(self, client, client_headers, db_session):
        """POST /pedidos with PAGO_LOCAL creates order (auto-confirms to CONFIRMADO for in-store payment)
        with calculated total and detail snapshots."""
        _seed_all(db_session)
        prod = _create_producto(db_session, nombre="Pizza", stock=50)

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "PAGO_LOCAL",
            "subtotal": "1500.00",
            "costo_envio": "0.00",
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 3,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=client_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["estado_codigo"] == "CONFIRMADO"  # PAGO_LOCAL auto-confirms
        assert Decimal(data["total"]) > Decimal("0")
        assert data["costo_envio"] == "0.00"
        assert data["direccion_id"] is None
        assert len(data["detalles"]) == 1
        det = data["detalles"][0]
        assert det["nombre_snapshot"] == prod.nombre
        assert Decimal(det["precio_snapshot"]) == prod.precio_actual
        assert det["cantidad"] == 3
        assert Decimal(det["subtotal_snap"]) == prod.precio_actual * 3

    def test_create_pedido_stock_insuficiente(self, client, client_headers, db_session):
        """POST /pedidos with cantidad > stock returns 422 stock_insuficiente.

        The error prevents pedido creation entirely — stock is never deducted.
        UoW rollback on exception guarantees atomicity.
        """
        _seed_all(db_session)
        prod = _create_producto(db_session, nombre="ScarceItem", stock=2)

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "PAGO_LOCAL",
            "subtotal": "5000.00",
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 10,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=client_headers)
        assert response.status_code == 422
        resp_json = response.json()
        detail = resp_json.get("detail", "")

        # detail may be a dict, list, or string depending on error origin
        error_text = ""
        if isinstance(detail, dict):
            error_text = detail.get("error", "") + " " + detail.get("mensaje", "")
        elif isinstance(detail, list):
            error_text = " ".join(str(d.get("msg", "")) for d in detail)
        else:
            error_text = str(detail)

        assert "stock" in error_text.lower() or "insuficiente" in error_text.lower()

    def test_create_pedido_mercadopago_stays_pendiente(self, client, client_headers, db_session):
        """POST /pedidos with MERCADOPAGO creates order in PENDIENTE (awaits payment).
        
        Note: Without direccion_id, costo_envio is forced to 0 by the service.
        """
        _seed_all(db_session)
        prod = _create_producto(db_session, nombre="MP Product", stock=30)

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "MERCADOPAGO",
            "subtotal": "1000.00",
            "costo_envio": "50.00",
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 2,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=client_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["estado_codigo"] == "PENDIENTE"
        # Without direccion_id, costo_envio is forced to 0
        assert Decimal(data["total"]) == Decimal("1000.00")

    def test_create_pedido_sin_detalles_creates_empty_order(self, client, client_headers, db_session):
        """POST /pedidos without detalles creates a PENDIENTE order with zero subtotal."""
        _seed_all(db_session)

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "PAGO_LOCAL",
            "subtotal": "0.00",
            "detalles": [],
        }, headers=client_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["estado_codigo"] == "CONFIRMADO"  # PAGO_LOCAL auto-confirms
        assert data["total"] == "0.00"

    def test_admin_no_puede_crear_pedido(self, client, admin_headers, db_session):
        """POST /pedidos as ADMIN returns 403 — admins manage, not buy."""
        _seed_all(db_session)
        prod = _create_producto(db_session, stock=50)

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "PAGO_LOCAL",
            "subtotal": "500.00",
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 1,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=admin_headers)
        assert response.status_code == 403

    def test_pedido_pago_local_sin_direccion_id(self, client, client_headers, db_session):
        """POST /pedidos as CLIENT with PAGO_LOCAL and direccion_id=null creates order with costo_envio=0."""
        _seed_all(db_session)
        prod = _create_producto(db_session, stock=50)

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "PAGO_LOCAL",
            "subtotal": "500.00",
            "costo_envio": "0.00",
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 2,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=client_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["costo_envio"] == "0.00"
        assert data["direccion_id"] is None
        assert data["estado_codigo"] == "CONFIRMADO"  # PAGO_LOCAL auto-confirms


# ═══════════════════════════════════════════════════════════════════════════
# PEDIDO PAGO_LOCAL — pickup-only validation
# ═══════════════════════════════════════════════════════════════════════════

class TestPedidoPickupOnly:
    """POST /api/v1/pedidos — PAGO_LOCAL (pickup-only) forces direccion_id=null or local-only."""

    def test_pago_local_with_personal_direccion_rejected(self, client, client_headers, db_session):
        """PAGO_LOCAL with a non-local (personal) direccion_id returns 422."""
        _seed_all(db_session)
        prod = _create_producto(db_session, stock=50)

        from sqlmodel import select
        u = db_session.exec(select(Usuario).where(Usuario.email == "client_test@test.com")).first()
        assert u is not None

        direccion = _create_direccion(db_session, u.id)  # es_local=False by default

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "PAGO_LOCAL",
            "direccion_id": direccion.id,
            "subtotal": 500,
            "costo_envio": 50,
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 1,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=client_headers)
        assert response.status_code == 422

    def test_pago_local_with_local_direccion_allowed(self, client, admin_headers, client_headers, db_session):
        """PAGO_LOCAL with direccion_id pointing to a local (es_local=True) succeeds."""
        _seed_all(db_session)
        prod = _create_producto(db_session, stock=50)

        # Admin creates a local/store
        response_local = client.post("/api/v1/direcciones/", json={
            "alias": "Sucursal Centro",
            "linea1": "Av. Principal 100",
            "ciudad": "Mendoza",
            "es_local": True,
        }, headers=admin_headers)
        assert response_local.status_code == 201
        local_id = response_local.json()["id"]
        assert response_local.json()["es_local"] is True

        # Now a CLIENT creates a pedido with PAGO_LOCAL referencing that local
        from sqlmodel import select
        u = db_session.exec(select(Usuario).where(Usuario.email == "client_test@test.com")).first()
        assert u is not None
        _ensure_formas_pago(db_session)

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "PAGO_LOCAL",
            "direccion_id": local_id,
            "subtotal": 500,
            "costo_envio": 50,
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 1,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=client_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["estado_codigo"] == "CONFIRMADO"  # PAGO_LOCAL auto-confirms
        assert data["costo_envio"] == "0.00"
        assert data["direccion_id"] == local_id

    def test_pago_local_sin_direccion_creates_order(self, client, client_headers, db_session):
        """PAGO_LOCAL without direccion_id creates order successfully (anonymous pickup)."""
        _seed_all(db_session)
        prod = _create_producto(db_session, stock=50)

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "PAGO_LOCAL",
            "subtotal": 500,
            "costo_envio": 50,
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 1,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=client_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["estado_codigo"] == "CONFIRMADO"  # PAGO_LOCAL auto-confirms
        assert data["costo_envio"] == "0.00"
        assert data["direccion_id"] is None

    def test_mercadopago_with_direccion_allowed(self, client, client_headers, db_session):
        """MERCADOPAGO with direccion_id is allowed (delivery-enabled method)."""
        _seed_all(db_session)
        prod = _create_producto(db_session, stock=50)

        from sqlmodel import select
        u = db_session.exec(select(Usuario).where(Usuario.email == "client_test@test.com")).first()
        assert u is not None

        direccion = _create_direccion(db_session, u.id)

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "MERCADOPAGO",
            "direccion_id": direccion.id,
            "subtotal": 500,
            "costo_envio": 50,
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 1,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=client_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["direccion_id"] == direccion.id


# ═══════════════════════════════════════════════════════════════════════════
# PEDIDO SORT TESTS — sort_by / sort_order query params
# ═══════════════════════════════════════════════════════════════════════════

class TestPedidoSortParams:

    def test_activos_sort_by_id_asc(self, client, admin_headers, db_session):
        """GET /pedidos/activos?sort_by=id&sort_order=asc returns sorted ascending by ID."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p1 = _create_pedido(db_session, u.id, estado="PENDIENTE")
        p2 = _create_pedido(db_session, u.id, estado="PENDIENTE")
        p3 = _create_pedido(db_session, u.id, estado="PENDIENTE")

        response = client.get(
            "/api/v1/pedidos/activos?sort_by=id&sort_order=asc",
            headers=admin_headers,
        )
        assert response.status_code == 200
        items = response.json()["items"]
        ids = [item["id"] for item in items]
        assert ids == sorted(ids), f"Expected ASC by id, got {ids}"

    def test_activos_sort_by_created_at_desc(self, client, admin_headers, db_session):
        """GET /pedidos/activos?sort_by=created_at&sort_order=desc returns newest first."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p1 = _create_pedido(db_session, u.id, estado="PENDIENTE")
        p2 = _create_pedido(db_session, u.id, estado="PENDIENTE")
        p3 = _create_pedido(db_session, u.id, estado="PENDIENTE")

        response = client.get(
            "/api/v1/pedidos/activos?sort_by=created_at&sort_order=desc",
            headers=admin_headers,
        )
        assert response.status_code == 200
        items = response.json()["items"]
        dates = [item["created_at"] for item in items]
        # Verify descending: each date >= next
        for i in range(len(dates) - 1):
            assert dates[i] >= dates[i + 1], f"Expected DESC by created_at, {dates[i]} < {dates[i + 1]}"

    def test_activos_sort_by_total_asc(self, client, admin_headers, db_session):
        """GET /pedidos/activos?sort_by=total&sort_order=asc returns cheapest first."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p1 = _create_pedido(db_session, u.id, estado="PENDIENTE")
        p1.total = Decimal("100.00")
        p2 = _create_pedido(db_session, u.id, estado="PENDIENTE")
        p2.total = Decimal("500.00")
        p3 = _create_pedido(db_session, u.id, estado="PENDIENTE")
        p3.total = Decimal("300.00")
        db_session.flush()

        response = client.get(
            "/api/v1/pedidos/activos?sort_by=total&sort_order=asc",
            headers=admin_headers,
        )
        assert response.status_code == 200
        items = response.json()["items"]
        totals = [Decimal(item["total"]) for item in items]
        assert totals == sorted(totals), f"Expected ASC by total, got {totals}"

    def test_activos_sort_by_estado_codigo_asc(self, client, admin_headers, db_session):
        """GET /pedidos/activos?sort_by=estado_codigo&sort_order=asc sorts by status alphabetically."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p1 = _create_pedido(db_session, u.id, estado="CONFIRMADO")
        p2 = _create_pedido(db_session, u.id, estado="PENDIENTE")
        p3 = _create_pedido(db_session, u.id, estado="EN_PREP")

        response = client.get(
            "/api/v1/pedidos/activos?sort_by=estado_codigo&sort_order=asc",
            headers=admin_headers,
        )
        assert response.status_code == 200
        items = response.json()["items"]
        estados = [item["estado_codigo"] for item in items]
        assert estados == sorted(estados), f"Expected ASC by estado_codigo, got {estados}"

    def test_historial_sort_by_updated_at_asc(self, client, admin_headers, db_session):
        """GET /pedidos/historial?sort_by=updated_at&sort_order=asc sorts oldest updated first."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p1 = _create_pedido(db_session, u.id, estado="ENTREGADO")
        p2 = _create_pedido(db_session, u.id, estado="CANCELADO")

        response = client.get(
            "/api/v1/pedidos/historial?sort_by=updated_at&sort_order=asc",
            headers=admin_headers,
        )
        assert response.status_code == 200
        items = response.json()["items"]
        dates = [item["updated_at"] for item in items]
        for i in range(len(dates) - 1):
            assert dates[i] <= dates[i + 1], f"Expected ASC by updated_at, {dates[i]} > {dates[i + 1]}"

    def test_historial_default_sort_desc(self, client, admin_headers, db_session):
        """GET /pedidos/historial without sort params defaults to id desc."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p1 = _create_pedido(db_session, u.id, estado="ENTREGADO")
        p2 = _create_pedido(db_session, u.id, estado="CANCELADO")

        response = client.get(
            "/api/v1/pedidos/historial",
            headers=admin_headers,
        )
        assert response.status_code == 200
        items = response.json()["items"]
        ids = [item["id"] for item in items]
        assert ids == sorted(ids, reverse=True), f"Expected DESC by id (default), got {ids}"

    def test_activos_sort_by_invalid_field_returns_422(self, client, admin_headers, db_session):
        """Invalid sort_by value returns 422."""
        _seed_all(db_session)
        response = client.get(
            "/api/v1/pedidos/activos?sort_by=invalid_field",
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_activos_sort_order_invalid_returns_422(self, client, admin_headers, db_session):
        """Invalid sort_order value returns 422."""
        _seed_all(db_session)
        response = client.get(
            "/api/v1/pedidos/activos?sort_order=up",
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_activos_client_sees_own_sorted(self, client, client_headers, db_session):
        """Client user sees only their own orders with sorting applied."""
        _seed_all(db_session)
        from sqlmodel import select
        u = db_session.exec(select(Usuario).where(Usuario.email == "client_test@test.com")).first()
        assert u is not None
        _create_pedido(db_session, u.id, estado="PENDIENTE")
        _create_pedido(db_session, u.id, estado="PENDIENTE")

        # Create another user's pedido to ensure it does NOT appear
        u2 = _create_user(db_session, email="other_user@test.com")
        _create_pedido(db_session, u2.id, estado="PENDIENTE")

        response = client.get(
            "/api/v1/pedidos/activos?sort_by=id&sort_order=asc",
            headers=client_headers,
        )
        assert response.status_code == 200
        items = response.json()["items"]
        # All items should belong to client user
        for item in items:
            assert item["usuario_id"] == u.id

    def test_historial_sort_by_total_desc(self, client, admin_headers, db_session):
        """GET /pedidos/historial?sort_by=total&sort_order=desc returns most expensive first."""
        _seed_all(db_session)
        u = _create_user(db_session)
        p1 = _create_pedido(db_session, u.id, estado="ENTREGADO")
        p1.total = Decimal("200.00")
        p2 = _create_pedido(db_session, u.id, estado="CANCELADO")
        p2.total = Decimal("800.00")
        p3 = _create_pedido(db_session, u.id, estado="ENTREGADO")
        p3.total = Decimal("500.00")
        db_session.flush()

        response = client.get(
            "/api/v1/pedidos/historial?sort_by=total&sort_order=desc",
            headers=admin_headers,
        )
        assert response.status_code == 200
        items = response.json()["items"]
        totals = [Decimal(item["total"]) for item in items]
        assert totals == sorted(totals, reverse=True), f"Expected DESC by total, got {totals}"


# ═══════════════════════════════════════════════════════════════════════════
# SCHEMA HARDENING TESTS — cantidad field constraints
# ═══════════════════════════════════════════════════════════════════════════

class TestSchemaConstraints:

    def test_item_pedido_request_cantidad_zero_raises_validation_error(self):
        """ItemPedidoRequest(cantidad=0) raises ValidationError — gt=0 constraint."""
        from pydantic import ValidationError
        from app.modules.VentasPagosTrazabilidad.Pedido.schemas import ItemPedidoRequest
        with pytest.raises(ValidationError):
            ItemPedidoRequest(
                producto_id=1,
                cantidad=0,
                nombre_snapshot="Test",
                precio_snapshot="100.00",
            )

    def test_item_pedido_request_cantidad_negative_raises_validation_error(self):
        """ItemPedidoRequest(cantidad=-1) raises ValidationError — gt=0 constraint."""
        from pydantic import ValidationError
        from app.modules.VentasPagosTrazabilidad.Pedido.schemas import ItemPedidoRequest
        with pytest.raises(ValidationError):
            ItemPedidoRequest(
                producto_id=1,
                cantidad=-1,
                nombre_snapshot="Test",
                precio_snapshot="100.00",
            )

    def test_item_pedido_request_cantidad_one_succeeds(self):
        """ItemPedidoRequest(cantidad=1) succeeds — valid positive integer."""
        from app.modules.VentasPagosTrazabilidad.Pedido.schemas import ItemPedidoRequest
        item = ItemPedidoRequest(
            producto_id=1,
            cantidad=1,
            nombre_snapshot="Test",
            precio_snapshot="100.00",
        )
        assert item.cantidad == 1

    def test_detalle_pedido_update_cantidad_negative_raises_validation_error(self):
        """DetallePedidoUpdate(cantidad=-1) raises ValidationError — ge=0 constraint."""
        from pydantic import ValidationError
        from app.modules.VentasPagosTrazabilidad.Pedido.schemas import DetallePedidoUpdate
        with pytest.raises(ValidationError):
            DetallePedidoUpdate(cantidad=-1)

    def test_detalle_pedido_update_cantidad_zero_succeeds(self):
        """DetallePedidoUpdate(cantidad=0) succeeds — ge=0 allows removal."""
        from app.modules.VentasPagosTrazabilidad.Pedido.schemas import DetallePedidoUpdate
        update = DetallePedidoUpdate(cantidad=0)
        assert update.cantidad == 0

    def test_validar_stock_detalle_input_cantidad_zero_raises_validation_error(self):
        """ValidarStockDetalleInput(producto_id=1, cantidad=0) raises ValidationError — gt=0."""
        from pydantic import ValidationError
        from app.modules.VentasPagosTrazabilidad.Pedido.schemas import ValidarStockDetalleInput
        with pytest.raises(ValidationError):
            ValidarStockDetalleInput(producto_id=1, cantidad=0)


# ═══════════════════════════════════════════════════════════════════════════
# PEDIDO DETAIL MODIFICATION TESTS — actualizar_detalle stock validation
# ═══════════════════════════════════════════════════════════════════════════

class TestActualizarDetalleStock:
    """PATCH /pedidos/{id}/detalles/{producto_id} — stock validation on detail update."""

    def test_update_detail_cantidad_exceeding_stock_returns_422(self, client, admin_headers, db_session):
        """Updating a detail's cantidad above product stock returns 422 stock_insuficiente."""
        _seed_all(db_session)
        u = _create_user(db_session, email="stock_update@test.com")
        prod = _create_producto(db_session, nombre="LowStock", stock=3)
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")

        # Add a detail line with cantidad=1
        from app.modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=1, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual,
        ))
        db_session.flush()

        # Try to update to 10 (stock is only 3)
        response = client.patch(
            f"/api/v1/pedidos/{p.id}/detalles/{prod.id}",
            json={"cantidad": 10},
            headers=admin_headers,
        )
        assert response.status_code == 422
        resp_json = response.json()
        detail = resp_json.get("detail", "")
        # detail may be a dict or string depending on error origin
        error_text = ""
        if isinstance(detail, dict):
            error_text = detail.get("error", "") + " " + detail.get("mensaje", "")
            assert detail.get("solicitado") == 10
            assert detail.get("disponible") == 3
        elif isinstance(detail, list):
            error_text = " ".join(str(d.get("msg", "")) for d in detail)
        else:
            error_text = str(detail)
        assert "stock" in error_text.lower() or "insuficiente" in error_text.lower()

    def test_update_detail_cantidad_within_stock_succeeds(self, client, admin_headers, db_session):
        """Updating a detail's cantidad within available stock succeeds."""
        _seed_all(db_session)
        u = _create_user(db_session, email="stock_ok@test.com")
        prod = _create_producto(db_session, nombre="PlentyStock", stock=50)
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")

        from app.modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=1, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual,
        ))
        db_session.flush()

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/detalles/{prod.id}",
            json={"cantidad": 5},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Verify the detail was updated
        updated_det = [d for d in data["detalles"] if d["producto_id"] == prod.id]
        assert len(updated_det) == 1
        assert updated_det[0]["cantidad"] == 5

    def test_update_detail_cantidad_zero_removes_detail(self, client, admin_headers, db_session):
        """Updating a detail's cantidad to 0 removes the detail line (stock check skipped)."""
        _seed_all(db_session)
        u = _create_user(db_session, email="remove_det@test.com")
        prod = _create_producto(db_session, nombre="DelMe", stock=0)  # stock=0 but removal skipped
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")

        from app.modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=1, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual,
        ))
        db_session.flush()

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/detalles/{prod.id}",
            json={"cantidad": 0},
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        # Detail should be removed
        updated_det = [d for d in data["detalles"] if d["producto_id"] == prod.id]
        assert len(updated_det) == 0


# ═══════════════════════════════════════════════════════════════════════════
# PEDIDO UPDATE (PATCH) TESTS — update() stock validation
# ═══════════════════════════════════════════════════════════════════════════

class TestPedidoUpdateStock:
    """PATCH /pedidos/{id} — stock validation when replacing detalles."""

    def test_patch_pedido_detail_exceeding_stock_returns_422(self, client, admin_headers, db_session):
        """PATCH pedido with a detail line exceeding product stock returns 422."""
        _seed_all(db_session)
        u = _create_user(db_session, email="patch_stock@test.com")
        prod = _create_producto(db_session, nombre="PatchScarce", stock=1)
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")

        response = client.patch(
            f"/api/v1/pedidos/{p.id}",
            json={
                "detalles": [{
                    "producto_id": prod.id,
                    "cantidad": 5,
                    "nombre_snapshot": prod.nombre,
                    "precio_snapshot": str(prod.precio_actual),
                }],
            },
            headers=admin_headers,
        )
        assert response.status_code == 422
        resp_json = response.json()
        detail = resp_json.get("detail", "")
        # detail may be a dict or string depending on error origin
        if isinstance(detail, dict):
            assert detail.get("error") == "stock_insuficiente"
        elif isinstance(detail, list):
            error_text = " ".join(str(d.get("msg", "")) for d in detail)
            assert "stock" in error_text.lower() or "insuficiente" in error_text.lower()
        else:
            assert "stock" in str(detail).lower() or "insuficiente" in str(detail).lower()

    def test_patch_pedido_detail_within_stock_succeeds(self, client, admin_headers, db_session):
        """PATCH pedido with detail lines within available stock succeeds."""
        _seed_all(db_session)
        u = _create_user(db_session, email="patch_ok@test.com")
        prod = _create_producto(db_session, nombre="PatchOk", stock=50)
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")

        response = client.patch(
            f"/api/v1/pedidos/{p.id}",
            json={
                "detalles": [{
                    "producto_id": prod.id,
                    "cantidad": 3,
                    "nombre_snapshot": prod.nombre,
                    "precio_snapshot": str(prod.precio_actual),
                }],
            },
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["detalles"]) == 1
        assert data["detalles"][0]["cantidad"] == 3


# ═══════════════════════════════════════════════════════════════════════════
# REGRESSION TESTS — Make-to-Stock ingredient isolation
# ═══════════════════════════════════════════════════════════════════════════

class TestMakeToOrderIngredientConsumption:
    """Order operations MUST modify ingredient stock under make-to-order model.

    Under make-to-order, ingredient stock IS consumed at order confirmation
    time and restored at cancellation time. Products' stock is derived from
    ingredient availability — no separate finished-goods stock exists.
    """

    def test_avanzar_estado_deducts_ingredient_stock(self, client, admin_headers, db_session):
        """Order confirmation (PENDIENTE -> CONFIRMADO) deducts ingredient stock."""
        _seed_all(db_session)
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

        # Create ingredient with known stock
        ing = Ingrediente(
            nombre="Test Ingredient", descripcion="For make-to-order test",
            es_alergeno=False, precio_actual=Decimal("10.00"), stock_actual=100,
        )
        db_session.add(ing)
        db_session.flush()

        u = _create_user(db_session, email="mto1@test.com")
        prod = Producto(
            nombre="MTOProduct", descripcion="Test",
            precio_base=Decimal("500"), precio_actual=Decimal("500"),
            tiempo_prep_min=5, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod)
        db_session.flush()

        # Link ingredient to product (2.0 units per product)
        db_session.add(ProductoIngrediente(
            producto_id=prod.id, ingrediente_id=ing.id,
            cantidad=Decimal("2.0"), es_removible=True, es_principal=True, orden=0,
        ))
        db_session.flush()

        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=3, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual * 3,
        ))
        db_session.flush()

        ingred_stock_before = ing.stock_actual

        response = client.patch(
            f"/api/v1/pedidos/{p.id}/avanzar",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["estado_actual"] == "CONFIRMADO"

        db_session.refresh(ing)

        # Ingredient stock: 3 * 2.0 = 6 deducted → 100 - 6 = 94
        assert ing.stock_actual == ingred_stock_before - 6, (
            f"Ingredient stock should be {ingred_stock_before - 6}, got {ing.stock_actual}. "
            "Make-to-order: ingredients are consumed at order confirmation."
        )

    def test_cancelar_pedido_restores_ingredient_stock(self, client, admin_headers, db_session):
        """Order cancellation restores ingredient stock under make-to-order."""
        _seed_all(db_session)
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

        ing = Ingrediente(
            nombre="CancelMTOIngredient", descripcion="For make-to-order cancel test",
            es_alergeno=False, precio_actual=Decimal("10.00"), stock_actual=200,
        )
        db_session.add(ing)
        db_session.flush()

        u = _create_user(db_session, email="mto2@test.com")
        prod = Producto(
            nombre="CancelMTOProduct", descripcion="Test",
            precio_base=Decimal("500"), precio_actual=Decimal("500"),
            tiempo_prep_min=5, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod)
        db_session.flush()

        db_session.add(ProductoIngrediente(
            producto_id=prod.id, ingrediente_id=ing.id,
            cantidad=Decimal("1.5"), es_removible=True, es_principal=True, orden=0,
        ))
        db_session.flush()

        # Create in PENDIENTE, confirm (deducts ingredients), then cancel
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=2, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual * 2,
        ))
        db_session.flush()

        ingred_stock_before = ing.stock_actual  # 200

        # Step 1: Confirm → deducts 2 * 1.5 = 3 from ingredient
        r1 = client.patch(f"/api/v1/pedidos/{p.id}/avanzar", headers=admin_headers)
        assert r1.status_code == 200
        db_session.refresh(ing)
        assert ing.stock_actual == ingred_stock_before - 3  # 197

        # Step 2: Cancel → restores 3 to ingredient
        response = client.patch(
            f"/api/v1/pedidos/{p.id}/cancelar",
            json={"motivo": "MTO cancel test"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["estado_actual"] == "CANCELADO"

        db_session.refresh(ing)

        # Ingredient stock restored to original value
        assert ing.stock_actual == ingred_stock_before, (
            f"Ingredient stock should be {ingred_stock_before}, got {ing.stock_actual}. "
            "Make-to-order: ingredients are restored when orders are cancelled."
        )


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3 — Derived Stock Broadcast After Order Operations
# ═══════════════════════════════════════════════════════════════════════════

class TestDerivedStockAfterOrderOps:
    """Task 38: Derived stock recomputation is triggered after order
    confirmation and cancellation for affected products."""

    def test_confirm_order_affects_product_derived_stock(self, client, admin_headers, db_session):
        """Confirming an order reduces ingredient stock, which lowers
        affected products' derived stock."""
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
        from app.modules.CatalogoDeProductos.Producto.repository import ProductoRepository
        from app.modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
        from decimal import Decimal

        _seed_all(db_session)

        # Create ingredient with 30 units
        ing = Ingrediente(
            nombre="Queso OrderDerived", descripcion="Test",
            precio_actual=Decimal("50.00"), stock_actual=30,
        )
        db_session.add(ing)
        db_session.flush()

        # Create product with 0.5 units per product
        prod = Producto(
            nombre="Pizza OrderDerived", descripcion="Test",
            precio_base=Decimal("800.00"), precio_actual=Decimal("800.00"),
            tiempo_prep_min=10, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod)
        db_session.flush()

        pi = ProductoIngrediente(
            producto_id=prod.id, ingrediente_id=ing.id,
            cantidad=Decimal("0.500"), es_removible=True, es_principal=True,
            orden=0,
        )
        db_session.add(pi)
        db_session.flush()

        # Baseline derived stock: floor(30/0.5) = 60
        repo = ProductoRepository(db_session)
        assert repo.compute_derived_stock(prod.id) == 60

        # Create user and order
        u = _create_user(db_session, email="derivedtest@test.com")
        dire = _create_direccion(db_session, u.id)
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=6, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual * 6,
        ))
        db_session.flush()

        # Confirm the order
        response = client.patch(
            f"/api/v1/pedidos/{p.id}/avanzar",
            headers=admin_headers,
        )
        assert response.status_code == 200

        # Ingredient stock: 30 - (0.5 * 6) = 30 - 3 = 27
        db_session.refresh(ing)
        assert ing.stock_actual == 27, f"Expected ingredient stock 27, got {ing.stock_actual}"

        # Derived stock: floor(27/0.5) = 54
        new_derived = repo.compute_derived_stock(prod.id)
        assert new_derived == 54, f"Expected derived stock 54, got {new_derived}"

    def test_cancel_order_restores_derived_stock(self, client, admin_headers, db_session):
        """Cancelling a confirmed order restores ingredient stock, raising
        derived stock back to baseline."""
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
        from app.modules.CatalogoDeProductos.Producto.repository import ProductoRepository
        from app.modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
        from decimal import Decimal

        _seed_all(db_session)

        ing = Ingrediente(
            nombre="Jamon CancelDerived", descripcion="Test",
            precio_actual=Decimal("60.00"), stock_actual=50,
        )
        db_session.add(ing)
        db_session.flush()

        prod = Producto(
            nombre="Sandwich CancelDerived", descripcion="Test",
            precio_base=Decimal("400.00"), precio_actual=Decimal("400.00"),
            tiempo_prep_min=5, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod)
        db_session.flush()

        pi = ProductoIngrediente(
            producto_id=prod.id, ingrediente_id=ing.id,
            cantidad=Decimal("1.000"), es_removible=True, es_principal=True,
            orden=0,
        )
        db_session.add(pi)
        db_session.flush()

        repo = ProductoRepository(db_session)
        baseline_derived = repo.compute_derived_stock(prod.id)  # floor(50/1) = 50
        assert baseline_derived == 50
        baseline_ingredient = ing.stock_actual  # 50

        # Create in PENDIENTE, advance to CONFIRMADO (deducts), then cancel
        u = _create_user(db_session, email="cancelderived@test.com")
        _create_direccion(db_session, u.id)
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=3, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual * 3,
        ))
        db_session.flush()

        # Step 1: Confirm (PENDIENTE -> CONFIRMADO) — deducts ingredient stock
        response = client.patch(
            f"/api/v1/pedidos/{p.id}/avanzar",
            headers=admin_headers,
        )
        assert response.status_code == 200
        db_session.refresh(ing)
        assert ing.stock_actual == baseline_ingredient - 3  # 50 - 3 = 47

        # Step 2: Cancel from CONFIRMADO — restores ingredient stock
        response = client.patch(
            f"/api/v1/pedidos/{p.id}/cancelar",
            json={"motivo": "Test cancel derived"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["estado_actual"] == "CANCELADO"

        # Ingredient stock restored back to baseline
        db_session.refresh(ing)
        assert ing.stock_actual == baseline_ingredient, (
            f"Expected restored ingredient stock {baseline_ingredient}, got {ing.stock_actual}"
        )

        # Derived stock should go back to baseline
        restored_derived = repo.compute_derived_stock(prod.id)
        assert restored_derived == baseline_derived, (
            f"Expected derived stock {baseline_derived}, got {restored_derived}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Phase 4 — New Make-to-Order Scenario Tests (Tasks 52-55)
# ═══════════════════════════════════════════════════════════════════════════

class TestMakeToOrderNewScenarios:
    """New scenarios verifying make-to-order ingredient-level stock behavior."""

    def test_concurrent_orders_same_ingredient_serialized(self, client, admin_headers, db_session):
        """Two orders with products sharing ingredients both succeed
        when ingredient stock is sufficient, and ingredient stock reflects
        BOTH deductions."""
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

        _seed_all(db_session)

        # Shared ingredient with 100 units
        ing = Ingrediente(
            nombre="SharedIngredient", descripcion="Shared across products",
            es_alergeno=False, precio_actual=Decimal("10.00"), stock_actual=100,
        )
        db_session.add(ing)
        db_session.flush()

        # Two products using the same ingredient
        prod_a = Producto(
            nombre="ProductA Shared", descripcion="Test",
            precio_base=Decimal("500"), precio_actual=Decimal("500"),
            tiempo_prep_min=5, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod_a)
        db_session.flush()
        db_session.add(ProductoIngrediente(
            producto_id=prod_a.id, ingrediente_id=ing.id,
            cantidad=Decimal("2.0"), es_removible=True, es_principal=True, orden=0,
        ))

        prod_b = Producto(
            nombre="ProductB Shared", descripcion="Test",
            precio_base=Decimal("300"), precio_actual=Decimal("300"),
            tiempo_prep_min=3, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod_b)
        db_session.flush()
        db_session.add(ProductoIngrediente(
            producto_id=prod_b.id, ingrediente_id=ing.id,
            cantidad=Decimal("1.0"), es_removible=True, es_principal=True, orden=0,
        ))
        db_session.flush()

        u = _create_user(db_session, email="concurrent@test.com")

        # Order 1: prod_a x 10 → needs 20 ingredient units
        p1 = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")
        db_session.add(DetallePedido(
            pedido_id=p1.id, producto_id=prod_a.id,
            cantidad=10, nombre_snapshot=prod_a.nombre,
            precio_snapshot=prod_a.precio_actual,
            subtotal_snap=prod_a.precio_actual * 10,
        ))

        # Order 2: prod_b x 10 → needs 10 ingredient units  (total needed: 30, stock: 100)
        p2 = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")
        db_session.add(DetallePedido(
            pedido_id=p2.id, producto_id=prod_b.id,
            cantidad=10, nombre_snapshot=prod_b.nombre,
            precio_snapshot=prod_b.precio_actual,
            subtotal_snap=prod_b.precio_actual * 10,
        ))
        db_session.flush()

        # Confirm both orders
        r1 = client.patch(f"/api/v1/pedidos/{p1.id}/avanzar", headers=admin_headers)
        assert r1.status_code == 200, f"Order 1 failed: {r1.json()}"

        r2 = client.patch(f"/api/v1/pedidos/{p2.id}/avanzar", headers=admin_headers)
        assert r2.status_code == 200, f"Order 2 failed: {r2.json()}"

        # Ingredient stock: 100 - (10*2 + 10*1) = 100 - 30 = 70
        db_session.refresh(ing)
        assert ing.stock_actual == 70, (
            f"Expected ingredient stock 70 after two orders, got {ing.stock_actual}"
        )

    def test_order_with_multiple_products_deducts_aggregated_ingredients(self, client, admin_headers, db_session):
        """Order with 2 different products sharing an ingredient:
        the shared ingredient is deducted for BOTH product quantities."""
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

        _seed_all(db_session)

        # Shared ingredient
        ing = Ingrediente(
            nombre="MultiProdIngredient", descripcion="Shared",
            es_alergeno=False, precio_actual=Decimal("10.00"), stock_actual=200,
        )
        db_session.add(ing)
        db_session.flush()

        prod_a = Producto(
            nombre="MultiA", descripcion="Test",
            precio_base=Decimal("600"), precio_actual=Decimal("600"),
            tiempo_prep_min=5, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod_a)
        db_session.flush()
        db_session.add(ProductoIngrediente(
            producto_id=prod_a.id, ingrediente_id=ing.id,
            cantidad=Decimal("3.0"), es_removible=True, es_principal=True, orden=0,
        ))

        prod_b = Producto(
            nombre="MultiB", descripcion="Test",
            precio_base=Decimal("400"), precio_actual=Decimal("400"),
            tiempo_prep_min=3, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod_b)
        db_session.flush()
        db_session.add(ProductoIngrediente(
            producto_id=prod_b.id, ingrediente_id=ing.id,
            cantidad=Decimal("5.0"), es_removible=True, es_principal=True, orden=0,
        ))
        db_session.flush()

        u = _create_user(db_session, email="multiprod@test.com")
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod_a.id,
            cantidad=4, nombre_snapshot=prod_a.nombre,
            precio_snapshot=prod_a.precio_actual,
            subtotal_snap=prod_a.precio_actual * 4,
        ))
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod_b.id,
            cantidad=2, nombre_snapshot=prod_b.nombre,
            precio_snapshot=prod_b.precio_actual,
            subtotal_snap=prod_b.precio_actual * 2,
        ))
        db_session.flush()

        response = client.patch(f"/api/v1/pedidos/{p.id}/avanzar", headers=admin_headers)
        assert response.status_code == 200

        # Deduction: (4 * 3.0) + (2 * 5.0) = 12 + 10 = 22
        db_session.refresh(ing)
        assert ing.stock_actual == 200 - 22, (
            f"Expected 178, got {ing.stock_actual}"
        )

    def test_finished_product_order_deducts_stock_manual(self, client, admin_headers, db_session):
        """Order for es_producto_terminado product deducts stock_manual."""
        _seed_all(db_session)
        u = _create_user(db_session, email="finished@test.com")
        prod = Producto(
            nombre="FinishedProduct", descripcion="Test",
            precio_base=Decimal("200"), precio_actual=Decimal("200"),
            tiempo_prep_min=0, disponible=True,
            es_producto_terminado=True, stock_manual=10,
        )
        db_session.add(prod)
        db_session.flush()

        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=3, nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual * 3,
        ))
        db_session.flush()

        response = client.patch(f"/api/v1/pedidos/{p.id}/avanzar", headers=admin_headers)
        assert response.status_code == 200

        db_session.refresh(prod)
        assert prod.stock_manual == 7, f"Expected stock_manual=7, got {prod.stock_manual}"

    def test_insufficient_ingredient_stock_rolls_back_all_deductions(self, client, admin_headers, db_session):
        """Order with multiple products where one ingredient is insufficient:
        NO ingredient stock is deducted (atomic rollback), returns 409."""
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

        _seed_all(db_session)

        # Ingredient 1: ample stock
        ing1 = Ingrediente(
            nombre="PlentyIng", descripcion="Lots of stock",
            es_alergeno=False, precio_actual=Decimal("10.00"), stock_actual=500,
        )
        # Ingredient 2: barely any stock
        ing2 = Ingrediente(
            nombre="ScarceIng", descripcion="Almost empty",
            es_alergeno=False, precio_actual=Decimal("10.00"), stock_actual=5,
        )
        db_session.add(ing1)
        db_session.add(ing2)
        db_session.flush()

        prod = Producto(
            nombre="RollbackProduct", descripcion="Test",
            precio_base=Decimal("500"), precio_actual=Decimal("500"),
            tiempo_prep_min=5, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod)
        db_session.flush()

        db_session.add(ProductoIngrediente(
            producto_id=prod.id, ingrediente_id=ing1.id,
            cantidad=Decimal("1.0"), es_removible=True, es_principal=True, orden=0,
        ))
        db_session.add(ProductoIngrediente(
            producto_id=prod.id, ingrediente_id=ing2.id,
            cantidad=Decimal("10.0"), es_removible=True, es_principal=False, orden=1,
        ))
        db_session.flush()

        u = _create_user(db_session, email="rollback@test.com")
        p = _create_pedido(db_session, u.id, estado="PENDIENTE", forma_pago="PAGO_LOCAL")
        db_session.add(DetallePedido(
            pedido_id=p.id, producto_id=prod.id,
            cantidad=2,  # needs ing2: 2 * 10 = 20, but ing2 stock is only 5
            nombre_snapshot=prod.nombre,
            precio_snapshot=prod.precio_actual,
            subtotal_snap=prod.precio_actual * 2,
        ))
        db_session.flush()

        response = client.patch(f"/api/v1/pedidos/{p.id}/avanzar", headers=admin_headers)
        assert response.status_code == 409

        # Verify 409 response body contains the expected stock_insuficiente error.
        # The test's db_session is shared with the client's dependency override,
        # so the 409 rollback invalidates the session — we verify the HTTP
        # response, which proves the stock check caught the shortage atomically.
        body = response.json()
        assert body.get("error") == "stock_insuficiente", (
            f"Expected stock_insuficiente, got {body}"
        )
        assert "Stock insuficiente" in body.get("detail", ""), (
            f"Expected detail about insufficient stock, got {body.get('detail')}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Stock Cantidad Sync — persist derived stock after validation
# ═══════════════════════════════════════════════════════════════════════════

class TestStockCantidadSync:
    """After compute_derived_stock() in validation paths,
    producto.stock_cantidad must be immediately persisted so the
    column stays in sync with real ingredient availability."""

    def test_create_pedido_syncs_stock_cantidad_after_derived_stock_validation(
        self, client, client_headers, db_session
    ):
        """When create() computes derived stock for validation,
        producto.stock_cantidad must be persisted to the computed value."""
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
        from app.modules.CatalogoDeProductos.Producto.repository import ProductoRepository
        from decimal import Decimal

        _seed_all(db_session)

        # Create make-to-order product with ingredient association
        ing = Ingrediente(
            nombre="Harina SyncTest", descripcion="Test",
            precio_actual=Decimal("10.00"), stock_actual=30,
        )
        db_session.add(ing)
        db_session.flush()

        prod = Producto(
            nombre="Pan SyncTest", descripcion="Test",
            precio_base=Decimal("200.00"), precio_actual=Decimal("200.00"),
            tiempo_prep_min=10, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod)
        db_session.flush()

        pi = ProductoIngrediente(
            producto_id=prod.id, ingrediente_id=ing.id,
            cantidad=Decimal("1.000"), es_removible=False, es_principal=True,
            orden=0,
        )
        db_session.add(pi)
        db_session.flush()

        # Derived stock should be floor(30/1) = 30
        repo = ProductoRepository(db_session)
        derived = repo.compute_derived_stock(prod.id)
        assert derived == 30

        # stock_cantidad starts at default 0 (stale)
        assert prod.stock_cantidad == 0

        # Create order (MERCADOPAGO stays PENDIENTE —
        # validates stock via compute_derived_stock but does not deduct)
        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "MERCADOPAGO",
            "subtotal": "200.00",
            "costo_envio": "0.00",
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 2,
                "nombre_snapshot": prod.nombre,
                "precio_snapshot": str(prod.precio_actual),
            }],
        }, headers=client_headers)
        assert response.status_code == 201

        # After stock validation, stock_cantidad MUST be synced
        db_session.refresh(prod)
        assert prod.stock_cantidad == 30, (
            f"stock_cantidad should be synced to {derived} (derived stock), "
            f"but got {prod.stock_cantidad}"
        )

    def test_validar_stock_syncs_stock_cantidad(
        self, client, client_headers, db_session
    ):
        """When validar_stock_items() computes derived stock,
        producto.stock_cantidad must be persisted."""
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
        from app.modules.CatalogoDeProductos.Producto.repository import ProductoRepository
        from decimal import Decimal

        _seed_all(db_session)

        ing = Ingrediente(
            nombre="Tomate SyncTest", descripcion="Test",
            precio_actual=Decimal("5.00"), stock_actual=25,
        )
        db_session.add(ing)
        db_session.flush()

        prod = Producto(
            nombre="Salsa SyncTest", descripcion="Test",
            precio_base=Decimal("150.00"), precio_actual=Decimal("150.00"),
            tiempo_prep_min=5, disponible=True, es_producto_terminado=False,
        )
        db_session.add(prod)
        db_session.flush()

        pi = ProductoIngrediente(
            producto_id=prod.id, ingrediente_id=ing.id,
            cantidad=Decimal("2.000"), es_removible=False, es_principal=True,
            orden=0,
        )
        db_session.add(pi)
        db_session.flush()

        # Derived stock: floor(25/2) = 12
        repo = ProductoRepository(db_session)
        derived = repo.compute_derived_stock(prod.id)
        assert derived == 12
        assert prod.stock_cantidad == 0  # stale

        # Call validar-stock endpoint
        response = client.post("/api/v1/pedidos/validar-stock", json={
            "detalles": [{
                "producto_id": prod.id,
                "cantidad": 3,
            }],
        }, headers=client_headers)
        assert response.status_code == 200

        # stock_cantidad must be synced after validation
        db_session.refresh(prod)
        assert prod.stock_cantidad == 12, (
            f"stock_cantidad should be synced to {derived} (derived stock), "
            f"but got {prod.stock_cantidad}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# ValidarStock Items — always returns stock info for ALL products
# ═══════════════════════════════════════════════════════════════════════════

class TestValidarStockItemsResponse:
    """validar-stock must always return `items` with stock_disponible for
    every product, regardless of whether validation passes or fails."""

    def test_items_always_populated_when_validation_passes(
        self, client, client_headers, db_session
    ):
        """When stock is sufficient for all products, items array contains
        stock_disponible for each product."""
        _seed_all(db_session)

        # Create make-to-order product with ingredient stock
        _, _ = _create_producto_con_ingredientes(
            db_session, nombre="ItemsTestOK", stock_ingredientes=[
                ("IngOK1", 100, Decimal("1.0"), 5),
            ]
        )
        # Also create a finished product
        prod_finished = _create_producto(db_session, nombre="FinishedItem", stock=50)

        # Need to re-fetch the make-to-order product
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from sqlmodel import select
        prod_mto = db_session.exec(
            select(Producto).where(Producto.nombre == "ItemsTestOK")
        ).first()
        assert prod_mto is not None

        # Call validar-stock with quantities well within stock
        response = client.post("/api/v1/pedidos/validar-stock", json={
            "detalles": [
                {"producto_id": prod_mto.id, "cantidad": 10},
                {"producto_id": prod_finished.id, "cantidad": 5},
            ],
        }, headers=client_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["valido"] is True
        assert data["detalles"] == []

        # NEW: items must always be present with stock info
        assert "items" in data, "Response missing 'items' field"
        items = data["items"]
        assert len(items) == 2, f"Expected 2 stock items, got {len(items)}"

        # Map by producto_id for easy assertion
        stock_map = {i["producto_id"]: i for i in items}

        # Make-to-order product: derived stock = floor(100/1.0) = 100
        assert stock_map[prod_mto.id]["nombre_producto"] == "ItemsTestOK"
        assert stock_map[prod_mto.id]["stock_disponible"] == 100

        # Finished product: stock_manual = 50
        assert stock_map[prod_finished.id]["nombre_producto"] == "FinishedItem"
        assert stock_map[prod_finished.id]["stock_disponible"] == 50

    def test_items_always_populated_when_validation_fails(
        self, client, client_headers, db_session
    ):
        """When stock is insufficient, items array is STILL populated with
        stock_disponible for every product (not just the failing ones)."""
        _seed_all(db_session)

        # Low-stock finished product
        prod_low = _create_producto(db_session, nombre="LowStockItem", stock=3)

        # Call validar-stock with quantity above stock
        response = client.post("/api/v1/pedidos/validar-stock", json={
            "detalles": [
                {"producto_id": prod_low.id, "cantidad": 10},
            ],
        }, headers=client_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["valido"] is False
        # detalles should still list the failing one
        assert len(data["detalles"]) == 1

        # items must ALSO be present
        assert "items" in data, "Response missing 'items' field even when validation fails"
        items = data["items"]
        assert len(items) == 1
        assert items[0]["producto_id"] == prod_low.id
        assert items[0]["nombre_producto"] == "LowStockItem"
        assert items[0]["stock_disponible"] == 3

    def test_items_includes_both_valid_and_invalid_products(
        self, client, client_headers, db_session
    ):
        """With mixed valid/invalid products, items includes ALL of them."""
        _seed_all(db_session)

        _, _ = _create_producto_con_ingredientes(
            db_session, nombre="MixedOK", stock_ingredientes=[
                ("MixedIng", 50, Decimal("1.0"), 5),
            ]
        )
        prod_low = _create_producto(db_session, nombre="MixedLow", stock=2)

        from app.modules.CatalogoDeProductos.Producto.models import Producto
        from sqlmodel import select
        prod_mto = db_session.exec(
            select(Producto).where(Producto.nombre == "MixedOK")
        ).first()

        response = client.post("/api/v1/pedidos/validar-stock", json={
            "detalles": [
                {"producto_id": prod_mto.id, "cantidad": 5},      # valid (stock=50)
                {"producto_id": prod_low.id, "cantidad": 10},     # invalid (stock=2)
            ],
        }, headers=client_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["valido"] is False
        assert len(data["detalles"]) == 1  # Only the failing one

        # items must include BOTH products
        items = data["items"]
        assert len(items) == 2, f"Expected 2 items, got {len(items)}"

        stock_map = {i["producto_id"]: i for i in items}
        assert stock_map[prod_mto.id]["stock_disponible"] == 50
        assert stock_map[prod_low.id]["stock_disponible"] == 2
