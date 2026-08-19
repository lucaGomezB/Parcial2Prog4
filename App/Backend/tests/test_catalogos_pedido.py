"""
Integration tests for catalogos de pedido.

Covers: EstadoPedido, FormaPago listings.
Uses real SQLite DB via conftest fixtures.
"""
import pytest
from fastapi import status
from sqlmodel import select

from app.modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
from app.modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago


def _seed_catalogos(db_session):
    """Ensure estados_pedido and formas_pago exist."""
    for codigo, desc, orden, terminal in [
        ("PENDIENTE", "Pendiente", 1, False),
        ("CONFIRMADO", "Confirmado", 2, False),
        ("EN_PREP", "En preparacion", 3, False),
        ("ENTREGADO", "Entregado", 4, True),
        ("CANCELADO", "Cancelado", 5, True),
    ]:
        if not db_session.exec(
            select(EstadoPedido).where(EstadoPedido.codigo == codigo)
        ).first():
            db_session.add(EstadoPedido(
                codigo=codigo, descripcion=desc,
                orden=orden, es_terminal=terminal,
            ))
    db_session.flush()

    for codigo, desc, hab in [
        ("MERCADOPAGO", "MercadoPago", True),
        ("EFECTIVO", "Efectivo", False),
        ("PAGO_LOCAL", "Pago en local", True),
        ("TRANSFERENCIA", "Transferencia", True),
        ("DESHABILITADO", "Metodo deshabilitado", False),
    ]:
        if not db_session.exec(
            select(FormaPago).where(FormaPago.codigo == codigo)
        ).first():
            db_session.add(FormaPago(
                codigo=codigo, descripcion=desc, habilitado=hab,
            ))
    db_session.flush()


# ═══════════════════════════════════════════════════════════════════════════
# ESTADO PEDIDO TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestEstadoPedido:

    def test_list_estados_pedido(self, client, admin_headers, db_session):
        """Admin/PEDIDOS can list all order states."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)

        response = client.get("/api/v1/estados-pedido/", headers=admin_headers)
        assert response.status_code == 200
        estados = response.json()
        assert isinstance(estados, list)
        assert len(estados) >= 5
        codigos = [e["codigo"] for e in estados]
        for required in ["PENDIENTE", "CONFIRMADO", "ENTREGADO", "CANCELADO"]:
            assert required in codigos

    def test_get_estado_by_codigo(self, client, admin_headers, db_session):
        """Get a specific order state by code."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)

        response = client.get("/api/v1/estados-pedido/ENTREGADO", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["codigo"] == "ENTREGADO"
        assert response.json()["es_terminal"] is True

    def test_estado_not_found_returns_404(self, client, admin_headers, db_session):
        """Non-existent estado returns 404."""
        _seed_roles(db_session)
        response = client.get("/api/v1/estados-pedido/NONEXISTENT", headers=admin_headers)
        assert response.status_code == 404

    def test_list_estados_client_rejected(self, client, client_headers, db_session):
        """Client cannot list estados (403)."""
        _seed_roles(db_session)
        response = client.get("/api/v1/estados-pedido/", headers=client_headers)
        assert response.status_code == 403

    def test_list_estados_unauthenticated_returns_401(self, client):
        """No auth returns 401."""
        response = client.get("/api/v1/estados-pedido/")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# FORMA PAGO TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestFormaPago:

    def test_list_formas_pago_only_habilitadas(self, client, admin_headers, db_session):
        """By default, only enabled payment methods are listed."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)

        response = client.get("/api/v1/formas-pago/", headers=admin_headers)
        assert response.status_code == 200
        formas = response.json()
        assert isinstance(formas, list)
        for fp in formas:
            assert fp["habilitado"] is True

    def test_list_formas_pago_incluir_deshabilitadas(self, client, admin_headers, db_session):
        """incluir_deshabilitadas=True shows all payment methods."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)

        response = client.get(
            "/api/v1/formas-pago/?incluir_deshabilitadas=true",
            headers=admin_headers,
        )
        assert response.status_code == 200
        formas = response.json()
        habilitated = len([f for f in formas if f["habilitado"]])
        disabled = len([f for f in formas if not f["habilitado"]])
        assert disabled >= 1  # DESHABILITADO should be included

    def test_get_forma_pago_by_codigo(self, client, admin_headers, db_session):
        """Get a specific payment method by code."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)

        response = client.get("/api/v1/formas-pago/EFECTIVO", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["codigo"] == "EFECTIVO"

    def test_forma_pago_not_found_returns_404(self, client, admin_headers, db_session):
        """Non-existent forma_pago returns 404."""
        _seed_roles(db_session)
        response = client.get("/api/v1/formas-pago/NONEXISTENT", headers=admin_headers)
        assert response.status_code == 404

    def test_list_formas_pago_client_rejected(self, client, client_headers, db_session):
        """Client CAN list payment methods, but only habilitado=True (fixed — was 403)."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)
        response = client.get("/api/v1/formas-pago/", headers=client_headers)
        assert response.status_code == 200
        formas = response.json()
        assert isinstance(formas, list)
        assert len(formas) > 0, "Should return at least one habilitado payment method"
        for fp in formas:
            assert fp["habilitado"] is True, "CLIENT should never see disabled methods"

    def test_list_formas_pago_client_only_habilitadas(self, client, client_headers, db_session):
        """CLIENT sees only habilitado=True methods; disabled methods (e.g. DESHABILITADO) are excluded."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)
        response = client.get("/api/v1/formas-pago/", headers=client_headers)
        assert response.status_code == 200
        formas = response.json()
        codigos = [f["codigo"] for f in formas]
        assert "DESHABILITADO" not in codigos, "DESHABILITADO should be excluded for CLIENT"
        assert "PAGO_LOCAL" in codigos
        assert "MERCADOPAGO" in codigos
        # EFECTIVO is disabled, should not appear
        assert "EFECTIVO" not in codigos

    def test_list_formas_pago_client_ignores_incluir_deshabilitadas(self, client, client_headers, db_session):
        """CLIENT passing ?incluir_deshabilitadas=true still gets only habilitado methods."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)
        response = client.get(
            "/api/v1/formas-pago/?incluir_deshabilitadas=true",
            headers=client_headers,
        )
        assert response.status_code == 200
        formas = response.json()
        for fp in formas:
            assert fp["habilitado"] is True, (
                "CLIENT should NEVER see disabled methods, even with incluir_deshabilitadas=true"
            )

    def test_list_formas_pago_unauthenticated_returns_401(self, client):
        """No auth returns 401."""
        response = client.get("/api/v1/formas-pago/")
        assert response.status_code == 401

    def test_efectivo_deshabilitado(self, client, admin_headers, db_session):
        """EFECTIVO does not appear in the enabled payment methods list — task 4.6."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)

        response = client.get("/api/v1/formas-pago/", headers=admin_headers)
        assert response.status_code == 200
        formas = response.json()
        codigos = [f["codigo"] for f in formas]
        assert "EFECTIVO" not in codigos  # EFECTIVO is disabled
        assert "PAGO_LOCAL" in codigos
        assert "MERCADOPAGO" in codigos

    def test_efectivo_no_habilitado(self, client, admin_headers, db_session):
        """EFECTIVO appears only when incluir_deshabilitadas=true, and shows habilitado=false."""
        _seed_catalogos(db_session)
        _seed_roles(db_session)

        # Without incluir_deshabilitadas — EFECTIVO should NOT appear
        response = client.get("/api/v1/formas-pago/", headers=admin_headers)
        assert response.status_code == 200
        codigos = [f["codigo"] for f in response.json()]
        assert "EFECTIVO" not in codigos

        # With incluir_deshabilitadas=true — EFECTIVO appears with habilitado=false
        response_all = client.get(
            "/api/v1/formas-pago/?incluir_deshabilitadas=true",
            headers=admin_headers,
        )
        assert response_all.status_code == 200
        formas = response_all.json()
        efectivo_entry = [f for f in formas if f["codigo"] == "EFECTIVO"]
        assert len(efectivo_entry) == 1, "EFECTIVO should appear with incluir_deshabilitadas=true"
        assert efectivo_entry[0]["habilitado"] is False


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _seed_roles(db_session):
    """Ensure system roles exist."""
    from app.modules.IdentidadYAcceso.Rol.models import Rol
    for codigo, nombre, desc in [
        ("ADMIN", "Administrador", ""),
        ("CLIENT", "Cliente", ""),
        ("PEDIDOS", "Pedidos", ""),
        ("STOCK", "Stock", ""),
    ]:
        if not db_session.exec(
            select(Rol).where(Rol.codigo == codigo)
        ).first():
            db_session.add(Rol(codigo=codigo, nombre=nombre, descripcion=desc))
    db_session.flush()
