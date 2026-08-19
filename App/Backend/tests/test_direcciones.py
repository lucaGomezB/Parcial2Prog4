"""
Integration tests for DireccionEntrega (Delivery Address / Pickup Locations).

Covers: CRUD for personal addresses, company stores (locales),
es_principal uniqueness, and cross-admin locale visibility.
Uses real SQLite DB via conftest fixtures.
"""
import pytest
from fastapi import status
from sqlmodel import select


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _seed_roles(db_session):
    """Ensure system roles exist."""
    from app.modules.IdentidadYAcceso.Rol.models import Rol
    for codigo, nombre in [
        ("ADMIN", "Admin"), ("CLIENT", "Client"),
    ]:
        if not db_session.exec(select(Rol).where(Rol.codigo == codigo)).first():
            db_session.add(Rol(codigo=codigo, nombre=nombre))
    db_session.flush()


# ═══════════════════════════════════════════════════════════════════════════
# LOCALES (COMPANY STORES / PICKUP LOCATIONS) TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestLocales:
    """Tests for company stores (es_local=True) and their visibility."""

    def test_crear_local_como_admin(self, client, admin_headers, db_session):
        """POST /direcciones as ADMIN with es_local=true creates a store location.
        
        Verification: response includes es_local=true and es_principal=false
        (locales are not personal principal addresses).
        """
        _seed_roles(db_session)

        response = client.post("/api/v1/direcciones/", json={
            "alias": "Sucursal Godoy Cruz",
            "linea1": "Av. San Martin 500",
            "ciudad": "Godoy Cruz",
            "provincia": "Mendoza",
            "es_local": True,
        }, headers=admin_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["es_local"] is True
        assert data["es_principal"] is False
        assert data["alias"] == "Sucursal Godoy Cruz"

    def test_listar_locales_cross_admin(self, client, admin_headers, db_session):
        """Admin A creates a local. Admin B (different user) can see it in GET /direcciones.
        
        Admins see ALL addresses across all users, including other admins' locales.
        """
        from app.modules.IdentidadYAcceso.Usuario.models import Usuario
        from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol
        from app.core.security.passwords import get_password_hash
        from app.core.security.tokens import TokenData, create_access_token
        from datetime import timedelta

        _seed_roles(db_session)

        # Admin A (the fixture admin) creates a local
        resp_create = client.post("/api/v1/direcciones/", json={
            "alias": "Sucursal Centro",
            "linea1": "Calle Principal 100",
            "ciudad": "Mendoza",
            "es_local": True,
        }, headers=admin_headers)
        assert resp_create.status_code == 201
        local_id = resp_create.json()["id"]

        # Admin B: create a second admin user
        admin_b = Usuario(
            nombre="AdminB", apellido="Test",
            email="admin_b_cross@test.com",
            password_hash=get_password_hash("test123"),
        )
        db_session.add(admin_b)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=admin_b.id, rol_codigo="ADMIN"))
        db_session.flush()

        token_data = TokenData(
            user_id=admin_b.id,
            email=admin_b.email,
            roles=["ADMIN"],
        )
        access_token = create_access_token(token_data, expires_delta=timedelta(minutes=30))
        admin_b_headers = {"Authorization": f"Bearer {access_token}"}

        # Admin B lists all direcciones — should see the local created by Admin A
        resp_list = client.get("/api/v1/direcciones/", headers=admin_b_headers)
        assert resp_list.status_code == 200
        direcciones = resp_list.json()
        ids = [d["id"] for d in direcciones]
        assert local_id in ids, (
            f"Admin B should see Admin A's local (id={local_id}) in cross-admin view. "
            f"Got IDs: {ids}"
        )

    def test_cliente_no_ve_locales_sin_incluir(self, client, admin_headers, client_headers, db_session):
        """Client calling GET /direcciones without incluir_locales does NOT see admin-created locales."""
        _seed_roles(db_session)

        # Admin creates a local
        resp_create = client.post("/api/v1/direcciones/", json={
            "alias": "Sucursal Las Heras",
            "linea1": "Av. Independencia 200",
            "ciudad": "Las Heras",
            "es_local": True,
        }, headers=admin_headers)
        assert resp_create.status_code == 201
        local_id = resp_create.json()["id"]

        # Client lists their own direcciones (without incluir_locales)
        resp_list = client.get("/api/v1/direcciones/", headers=client_headers)
        assert resp_list.status_code == 200
        direcciones = resp_list.json()
        ids = [d["id"] for d in direcciones]
        assert local_id not in ids, (
            f"Client without incluir_locales should NOT see admin-created local "
            f"(id={local_id}). Got IDs: {ids}"
        )

    def test_cliente_ve_locales_con_incluir_locales(self, client, admin_headers, client_headers, db_session):
        """Client calling GET /direcciones?incluir_locales=true sees admin-created locales."""
        _seed_roles(db_session)

        # Admin creates a local
        resp_create = client.post("/api/v1/direcciones/", json={
            "alias": "Sucursal Lujan",
            "linea1": "Ruta 60 km 5",
            "ciudad": "Lujan de Cuyo",
            "es_local": True,
        }, headers=admin_headers)
        assert resp_create.status_code == 201
        local_id = resp_create.json()["id"]

        # Client lists direcciones WITH incluir_locales=true
        resp_list = client.get(
            "/api/v1/direcciones/?incluir_locales=true",
            headers=client_headers,
        )
        assert resp_list.status_code == 200
        direcciones = resp_list.json()
        ids = [d["id"] for d in direcciones]
        assert local_id in ids, (
            f"Client with incluir_locales=true should see admin-created local "
            f"(id={local_id}). Got IDs: {ids}"
        )

    def test_cliente_no_puede_crear_local(self, client, client_headers, db_session):
        """CLIENT POST /direcciones with es_local=True returns 403 Forbidden."""
        _seed_roles(db_session)

        response = client.post("/api/v1/direcciones/", json={
            "alias": "Intento Local",
            "linea1": "Calle Falsa 123",
            "ciudad": "Mendoza",
            "es_local": True,
        }, headers=client_headers)

        assert response.status_code == 403
        detail = response.json().get("detail", "")
        assert "administradores" in detail.lower()

    def test_cliente_crea_direccion_normal(self, client, client_headers, db_session):
        """CLIENT POST /direcciones with es_local=False creates successfully (regression)."""
        _seed_roles(db_session)

        response = client.post("/api/v1/direcciones/", json={
            "alias": "Mi Casa",
            "linea1": "Calle Verdadera 456",
            "ciudad": "Mendoza",
            "es_local": False,
        }, headers=client_headers)

        assert response.status_code == 201
        data = response.json()
        assert data["es_local"] is False
        assert data["alias"] == "Mi Casa"

    def test_cliente_no_puede_actualizar_a_local(self, client, client_headers, db_session):
        """CLIENT creates regular address, then PATCH with es_local=True returns 403."""
        _seed_roles(db_session)

        # First, client creates a regular address
        resp_create = client.post("/api/v1/direcciones/", json={
            "alias": "Mi Direccion",
            "linea1": "Calle Normal 789",
            "ciudad": "Mendoza",
            "es_local": False,
        }, headers=client_headers)
        assert resp_create.status_code == 201
        addr_id = resp_create.json()["id"]

        # Then, client tries to update it to local
        resp_patch = client.patch(
            f"/api/v1/direcciones/{addr_id}",
            json={"es_local": True},
            headers=client_headers,
        )

        assert resp_patch.status_code == 403
        detail = resp_patch.json().get("detail", "")
        assert "administradores" in detail.lower()


# ═══════════════════════════════════════════════════════════════════════════
# ES_PRINCIPAL (DEFAULT ADDRESS) TESTS
# ═══════════════════════════════════════════════════════════════════════════

class TestDireccionPrincipal:
    """Tests for the es_principal flag: uniqueness and admin behavior."""

    def test_cliente_solo_una_principal(self, client, client_headers, db_session):
        """Creating two addresses with es_principal=true results in only the last one being principal.
        
        The service atomically unsets the previous principal when a new one is created.
        """
        _seed_roles(db_session)

        # Create first address with es_principal=True
        resp1 = client.post("/api/v1/direcciones/", json={
            "alias": "Casa Principal",
            "linea1": "Calle Primera 123",
            "ciudad": "Mendoza",
            "es_principal": True,
        }, headers=client_headers)
        assert resp1.status_code == 201
        addr1_id = resp1.json()["id"]
        assert resp1.json()["es_principal"] is True

        # Create second address also with es_principal=True
        resp2 = client.post("/api/v1/direcciones/", json={
            "alias": "Oficina",
            "linea1": "Av. Trabajo 456",
            "ciudad": "Mendoza",
            "es_principal": True,
        }, headers=client_headers)
        assert resp2.status_code == 201
        addr2_id = resp2.json()["id"]
        assert resp2.json()["es_principal"] is True

        # Verify the first address is NO LONGER principal
        resp_get = client.get(f"/api/v1/direcciones/{addr1_id}", headers=client_headers)
        assert resp_get.status_code == 200
        assert resp_get.json()["es_principal"] is False, (
            f"Address {addr1_id} should have been unset as principal "
            f"when address {addr2_id} was created."
        )

        # Verify the second address IS the only principal
        resp_get2 = client.get(f"/api/v1/direcciones/{addr2_id}", headers=client_headers)
        assert resp_get2.status_code == 200
        assert resp_get2.json()["es_principal"] is True

        # Verify the list endpoint also shows only one principal
        resp_list = client.get("/api/v1/direcciones/", headers=client_headers)
        assert resp_list.status_code == 200
        direcciones = resp_list.json()
        principales = [d for d in direcciones if d["es_principal"]]
        assert len(principales) == 1, (
            f"Expected exactly 1 principal address, got {len(principales)}: {principales}"
        )

    def test_admin_setea_principal_en_su_propia_direccion(self, client, admin_headers, db_session):
        """Admin can set an address as principal via PATCH /direcciones/{id}/principal.
        
        Admin manages locales, but the set_principal endpoint works for admin-owned
        addresses as well. The semantics: admin addresses are for store management,
        not personal delivery, but the endpoint does not prevent admin from marking
        an address as principal.
        """
        _seed_roles(db_session)

        # Admin creates an address (not a local, just a regular address)
        resp_create = client.post("/api/v1/direcciones/", json={
            "alias": "Admin Personal",
            "linea1": "Calle Admin 789",
            "ciudad": "Mendoza",
            "es_principal": False,
        }, headers=admin_headers)
        assert resp_create.status_code == 201
        addr_id = resp_create.json()["id"]

        # Admin sets it as principal
        resp_patch = client.patch(
            f"/api/v1/direcciones/{addr_id}/principal",
            headers=admin_headers,
        )
        assert resp_patch.status_code == 200
        data = resp_patch.json()
        assert data["es_principal"] is True
        assert data["id"] == addr_id
