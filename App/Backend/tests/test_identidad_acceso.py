"""
Integration tests for Identidad & Acceso module.

Covers: Auth (register, login, me, logout, refresh), Usuario CRUD,
Rol listing, DireccionEntrega CRUD.

Uses real SQLite DB via conftest fixtures (no mocks for DB layer).
Auth headers use real JWT tokens to bypass rate limiter.
"""
import pytest
from fastapi import status
from sqlmodel import select

from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from app.modules.IdentidadYAcceso.Rol.models import Rol
from app.modules.IdentidadYAcceso.Usuario.repository import UsuarioRepository
from app.modules.IdentidadYAcceso.Usuario.service import obtener_usuario
from app.core.security.passwords import get_password_hash


# ═══════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class TestAuthRegister:
    """POST /api/v1/auth/register"""

    def test_register_creates_user_and_returns_tokens(self, client, db_session):
        """Happy path: register a new user, get access token + refresh cookie."""
        response = client.post("/api/v1/auth/register", json={
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "email": "nuevo@test.com",
            "password": "secure123",
        })
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "refresh_token" in response.cookies

    def test_register_duplicate_email_fails(self, client, db_session):
        """Registering the same email twice returns 409 Conflict."""
        payload = {
            "nombre": "Dup", "apellido": "User",
            "email": "dup@test.com", "password": "pass123",
        }
        r1 = client.post("/api/v1/auth/register", json=payload)
        assert r1.status_code == status.HTTP_201_CREATED
        r2 = client.post("/api/v1/auth/register", json=payload)
        assert r2.status_code == status.HTTP_409_CONFLICT

    def test_register_forces_client_role(self, client, db_session):
        """Registration always creates CLIENT role regardless of input."""
        response = client.post("/api/v1/auth/register", json={
            "nombre": "Force", "apellido": "Client",
            "email": "forceclient2@test.com", "password": "pass123",
            "roles_codigos": "ADMIN",
        })
        assert response.status_code == status.HTTP_201_CREATED

        # Verify via DB: the user should only have CLIENT role
        user = db_session.exec(
            select(Usuario).where(Usuario.email == "forceclient2@test.com")
        ).first()
        assert user is not None
        user_roles = db_session.exec(
            select(UsuarioRol.rol_codigo).where(UsuarioRol.usuario_id == user.id)
        ).all()
        assert "CLIENT" in user_roles
        assert "ADMIN" not in user_roles

    def test_register_missing_name_fails_validation(self, client):
        """Register without nombre returns 422."""
        response = client.post("/api/v1/auth/register", json={
            "apellido": "NoName", "email": "noname@test.com", "password": "pass123",
        })
        assert response.status_code == 422

    def test_register_invalid_email_fails(self, client):
        """Register with invalid email returns 422."""
        response = client.post("/api/v1/auth/register", json={
            "nombre": "Bad", "apellido": "Email",
            "email": "not-an-email", "password": "pass123",
        })
        assert response.status_code == 422


class TestAuthLogin:
    """POST /api/v1/auth/login"""

    def test_login_with_valid_credentials(self, client, db_session):
        """Login returns tokens for valid credentials."""
        client.post("/api/v1/auth/register", json={
            "nombre": "Login", "apellido": "Test",
            "email": "login_test@test.com", "password": "pass123",
        })
        response = client.post("/api/v1/auth/login", json={
            "email": "login_test@test.com", "password": "pass123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in response.cookies

    def test_login_with_invalid_password_returns_401(self, client, db_session):
        """Login with wrong password returns 401."""
        client.post("/api/v1/auth/register", json={
            "nombre": "BadPw", "apellido": "Test",
            "email": "badpw@test.com", "password": "correct123",
        })
        response = client.post("/api/v1/auth/login", json={
            "email": "badpw@test.com", "password": "wrong_password",
        })
        assert response.status_code == 401

    def test_login_with_nonexistent_email_returns_401(self, client):
        """Login with non-existent email returns 401."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com", "password": "pass123",
        })
        assert response.status_code == 401

    def test_login_missing_password_fails_validation(self, client):
        """Login without password returns 422."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@test.com",
        })
        assert response.status_code == 422

    def test_rate_limit_blocks_after_max_attempts(self, client, db_session):
        """After 5 failed login attempts, the 6th returns 429 with Retry-After."""
        # Reset limiter storage before test to ensure a clean slate
        # (previous tests may have consumed rate limit quota for this IP)
        try:
            from main import app
            app.state.limiter.reset()
        except Exception:
            pass

        # Register a user so we can make valid-but-failed login attempts
        client.post("/api/v1/auth/register", json={
            "nombre": "RL", "apellido": "Test",
            "email": "ratelimit@test.com", "password": "correct123",
        })
        # Make 5 failed login attempts
        for _ in range(5):
            resp = client.post("/api/v1/auth/login", json={
                "email": "ratelimit@test.com", "password": "wrong",
            })
            assert resp.status_code == 401
        # 6th attempt should be blocked
        blocked = client.post("/api/v1/auth/login", json={
            "email": "ratelimit@test.com", "password": "wrong",
        })
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers
        # Reset limiter so subsequent tests are not affected
        try:
            from main import app
            app.state.limiter.reset()
        except Exception:
            pass


class TestAuthMe:
    """GET /api/v1/auth/me"""

    def test_me_returns_user_profile(self, client, client_headers, db_session):
        """GET /auth/me returns the authenticated user's profile.

        Uses client_headers fixture's pre-created user instead of
        registering inline, to avoid transaction visibility issues
        with selectinload role loading in test transactions.
        """
        response = client.get("/api/v1/auth/me", headers=client_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "client_test@test.com"
        assert data["nombre"] == "Client"
        assert "CLIENT" in data["roles"]

    def test_me_without_token_returns_401(self, client):
        """GET /auth/me without Authorization header returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        """GET /auth/me with invalid token returns 401."""
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid_token_here",
        })
        assert response.status_code == 401


class TestAuthLogout:
    """POST /api/v1/auth/logout"""

    def test_logout_clears_refresh_cookie(self, client, db_session):
        """Logout clears the refresh_token cookie."""
        reg = client.post("/api/v1/auth/register", json={
            "nombre": "Logout", "apellido": "Test",
            "email": "logout_test@test.com", "password": "pass123",
        })
        token = reg.json()["access_token"]
        response = client.post("/api/v1/auth/logout", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_logout_revokes_token_in_db(self, client, db_session):
        """Logout sets revoked_at on the refresh token in the database."""
        from app.modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
        reg = client.post("/api/v1/auth/register", json={
            "nombre": "LogoutDB", "apellido": "Test",
            "email": "logoutdb@test.com", "password": "pass123",
        })
        token = reg.json()["access_token"]
        # Get the refresh token hash from DB before logout
        tokens_before = db_session.exec(
            select(RefreshToken).where(RefreshToken.revoked_at == None)
        ).all()
        assert len(tokens_before) >= 1, "At least one active refresh token must exist"

        response = client.post("/api/v1/auth/logout", headers={
            "Authorization": f"Bearer {token}",
        })
        assert response.status_code == 200

        # Verify at least one token was revoked (revoked_at IS NOT NULL)
        tokens_after = db_session.exec(
            select(RefreshToken).where(
                RefreshToken.revoked_at != None,
                RefreshToken.id.in_([t.id for t in tokens_before]),
            )
        ).all()
        assert len(tokens_after) >= 1, "Refresh token should be revoked in DB"

    def test_logout_without_token_returns_200(self, client):
        """Logout without a token returns 200 (idempotent)."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200


class TestAuthRefresh:
    """POST /api/v1/auth/refresh"""

    def test_refresh_with_valid_cookie_returns_new_tokens(self, client, db_session):
        """Refresh with a valid cookie returns new access token."""
        reg = client.post("/api/v1/auth/register", json={
            "nombre": "Refresh", "apellido": "Test",
            "email": "refresh_test@test.com", "password": "pass123",
        })
        refresh_cookie = reg.cookies.get("refresh_token")
        assert refresh_cookie, "Registration should set refresh_token cookie"

        # Use the cookie for refresh
        client.cookies.set("refresh_token", refresh_cookie)
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_refresh_without_cookie_returns_401(self, client):
        """Refresh without cookie returns 401."""
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# USUARIO ENDPOINTS (ADMIN only)
# ═══════════════════════════════════════════════════════════════════════════

class TestUsuarioList:
    """GET /api/v1/usuarios"""

    def test_list_usuarios_admin(self, client, admin_headers, db_session):
        """Admin can list all users."""
        u = Usuario(
            nombre="ListTest", apellido="User",
            email="list@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add(u)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="CLIENT"))
        db_session.flush()

        response = client.get("/api/v1/usuarios/", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2  # admin + created user

    def test_list_usuarios_client_rejected(self, client, client_headers):
        """Client role cannot list users (403)."""
        response = client.get("/api/v1/usuarios/", headers=client_headers)
        assert response.status_code == 403

    def test_list_usuarios_unauthenticated_returns_401(self, client):
        """No auth returns 401."""
        response = client.get("/api/v1/usuarios/")
        assert response.status_code == 401

    def test_list_usuarios_with_role_filter(self, client, admin_headers, db_session):
        """Filter usuarios by role code."""
        u = Usuario(
            nombre="Pedidos", apellido="Filter",
            email="pedidos_filter@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add(u)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="PEDIDOS"))
        db_session.flush()

        response = client.get(
            "/api/v1/usuarios/?rol_codigo=PEDIDOS", headers=admin_headers
        )
        assert response.status_code == 200
        items = response.json()["items"]
        for item in items:
            roles = [r["codigo"] for r in item["roles"]]
            assert "PEDIDOS" in roles

    def test_list_usuarios_pagination(self, client, admin_headers, db_session):
        """Pagination parameters are respected."""
        for i in range(3):
            u = Usuario(
                nombre=f"Page{i}", apellido="User",
                email=f"page{i}@test.com",
                password_hash=get_password_hash("pass"),
            )
            db_session.add(u)
            db_session.flush()
            db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="CLIENT"))
            db_session.flush()

        response = client.get(
            "/api/v1/usuarios/?skip=0&limit=2", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2


class TestUsuarioGetById:
    """GET /api/v1/usuarios/{id}"""

    def test_get_usuario_by_id_admin(self, client, admin_headers, db_session):
        """Admin can get a user by ID."""
        u = Usuario(
            nombre="GetById", apellido="Test",
            email="getbyid@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add(u)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="CLIENT"))
        db_session.flush()

        response = client.get(
            f"/api/v1/usuarios/{u.id}", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["email"] == "getbyid@test.com"

    def test_get_usuario_not_found_returns_404(self, client, admin_headers):
        """Non-existent user returns 404."""
        response = client.get("/api/v1/usuarios/99999", headers=admin_headers)
        assert response.status_code == 404


class TestUsuarioPatchSoftDelete:
    """PATCH /api/v1/usuarios/{id} and DELETE /api/v1/usuarios/{id}"""

    def test_patch_update_usuario(self, client, admin_headers, db_session):
        """Admin can update user fields."""
        u = Usuario(
            nombre="PatchMe", apellido="Now",
            email="patchme@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add(u)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="CLIENT"))
        db_session.flush()

        response = client.patch(
            f"/api/v1/usuarios/{u.id}",
            json={"celular": "1234567890"},
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["celular"] == "1234567890"

        # Verify in DB
        repo = UsuarioRepository(db_session)
        updated = repo.get_by_id(u.id)
        assert updated.celular == "1234567890"

    def test_soft_delete_usuario(self, client, admin_headers, db_session):
        """Admin can soft-delete a user (204)."""
        u = Usuario(
            nombre="DeleteMe", apellido="Now",
            email="deleteme@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add(u)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="CLIENT"))
        db_session.flush()

        response = client.delete(
            f"/api/v1/usuarios/{u.id}", headers=admin_headers
        )
        assert response.status_code == 204

        # Verify user is not found normally (soft-deleted)
        normal_lookup = obtener_usuario(db_session, u.id, incluir_eliminados=False)
        assert normal_lookup is None

    def test_rbac_guards_usuarios(self, client, client_headers):
        """Client cannot access usuario management endpoints."""
        endpoints = [
            ("get", "/api/v1/usuarios/"),
            ("get", "/api/v1/usuarios/1"),
            ("patch", "/api/v1/usuarios/1"),
            ("delete", "/api/v1/usuarios/1"),
        ]
        for method, path in endpoints:
            func = getattr(client, method)
            resp = func(path, headers=client_headers)
            assert resp.status_code in (403, 404), f"{method} {path} returned {resp.status_code}"


# ═══════════════════════════════════════════════════════════════════════════
# USUARIO SEARCH ENDPOINT — /api/v1/usuarios/?search=
# ═══════════════════════════════════════════════════════════════════════════

class TestUsuarioSearch:
    """GET /api/v1/usuarios?search= — textual search on nombre/apellido/email."""

    def test_search_by_partial_name(self, client, admin_headers, db_session):
        """Search 'juan' matches nombre 'Juan' and apellido 'Juana'."""
        u1 = Usuario(
            nombre="Juan", apellido="Perez",
            email="juan@test.com",
            password_hash=get_password_hash("pass"),
        )
        u2 = Usuario(
            nombre="Maria", apellido="Juana",
            email="maria@test.com",
            password_hash=get_password_hash("pass"),
        )
        u3 = Usuario(
            nombre="Pedro", apellido="Gomez",
            email="pedro@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add_all([u1, u2, u3])
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u1.id, rol_codigo="ADMIN"))
        db_session.add(UsuarioRol(usuario_id=u2.id, rol_codigo="CLIENT"))
        db_session.add(UsuarioRol(usuario_id=u3.id, rol_codigo="PEDIDOS"))
        db_session.flush()

        response = client.get("/api/v1/usuarios/?search=juan", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        emails = [item["email"] for item in data["items"]]
        assert "juan@test.com" in emails
        assert "maria@test.com" in emails
        assert "pedro@test.com" not in emails

    def test_search_combined_with_role_filter(self, client, admin_headers, db_session):
        """Search 'juan' + rol_codigo=ADMIN returns only the ADMIN match."""
        u1 = Usuario(
            nombre="Juan", apellido="Perez",
            email="juanp@test.com",
            password_hash=get_password_hash("pass"),
        )
        u2 = Usuario(
            nombre="Juana", apellido="Lopez",
            email="juana_lopez@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add_all([u1, u2])
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u1.id, rol_codigo="ADMIN"))
        db_session.add(UsuarioRol(usuario_id=u2.id, rol_codigo="CLIENT"))
        db_session.flush()

        response = client.get(
            "/api/v1/usuarios/?search=juan&rol_codigo=ADMIN",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "juanp@test.com"

    def test_search_no_results(self, client, admin_headers, db_session):
        """Search for a non-existent term returns empty list."""
        u = Usuario(
            nombre="Existente", apellido="User",
            email="exist@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add(u)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="CLIENT"))
        db_session.flush()

        response = client.get(
            "/api/v1/usuarios/?search=xyznotfound",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_search_empty_param(self, client, admin_headers, db_session):
        """Empty search param returns all users (same as omitting search)."""
        u = Usuario(
            nombre="EmptySearch", apellido="Test",
            email="emptysearch@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add(u)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="CLIENT"))
        db_session.flush()

        # With empty search
        r1 = client.get("/api/v1/usuarios/?search=", headers=admin_headers)
        # Without search param
        r2 = client.get("/api/v1/usuarios/", headers=admin_headers)

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["total"] == r2.json()["total"]

    def test_search_with_pagination(self, client, admin_headers, db_session):
        """Search + pagination: total reflects filtered count, items respect limit."""
        for i in range(5):
            u = Usuario(
                nombre=f"Mar{i}", apellido="Test",
                email=f"mar{i}@test.com",
                password_hash=get_password_hash("pass"),
            )
            db_session.add(u)
            db_session.flush()
            db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="CLIENT"))
            db_session.flush()

        response = client.get(
            "/api/v1/usuarios/?search=mar&skip=0&limit=3",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["skip"] == 0
        assert data["limit"] == 3

    def test_search_sql_injection_attempt(self, client, admin_headers, db_session):
        """Search with SQL injection characters returns no results without crashing."""
        u = Usuario(
            nombre="Safe", apellido="User",
            email="safe@test.com",
            password_hash=get_password_hash("pass"),
        )
        db_session.add(u)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=u.id, rol_codigo="CLIENT"))
        db_session.flush()

        response = client.get(
            "/api/v1/usuarios/?search='; DROP TABLE usuario--",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        # Should return empty results (no crash / no table damage)
        assert isinstance(data["items"], list)

    def test_search_client_rejected(self, client, client_headers):
        """Client role cannot search users (403)."""
        response = client.get("/api/v1/usuarios/?search=juan", headers=client_headers)
        assert response.status_code == 403

    def test_search_unauthenticated_returns_401(self, client):
        """No auth returns 401."""
        response = client.get("/api/v1/usuarios/?search=juan")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# USUARIO CREATE / UPDATE — asignado_por_id tracking
# ═══════════════════════════════════════════════════════════════════════════

class TestUsuarioCreateAsignadoPorId:
    """POST /api/v1/usuarios — verify asignado_por_id is populated."""

    def test_create_user_populates_asignado_por_id(self, client, admin_headers, db_session):
        """When admin creates a user with roles, UsuarioRol.asignado_por_id
        must be set to the admin's user ID."""
        # Seed roles first (Rol table needed for FK constraints)
        from app.modules.IdentidadYAcceso.Rol.models import Rol
        from sqlmodel import select as _select
        for codigo, nombre in [
            ("ADMIN", "Admin"), ("CLIENT", "Client"),
            ("PEDIDOS", "Pedidos"), ("STOCK", "Stock"),
        ]:
            if not db_session.exec(_select(Rol).where(Rol.codigo == codigo)).first():
                db_session.add(Rol(codigo=codigo, nombre=nombre))
        db_session.flush()

        # Find the admin user (created by admin_headers fixture)
        admin_user = db_session.exec(
            _select(Usuario).where(Usuario.email == "admin_test@test.com")
        ).first()
        assert admin_user is not None

        response = client.post("/api/v1/usuarios/", json={
            "nombre": "NewUser",
            "apellido": "WithRoles",
            "email": "newuser_roles@test.com",
            "password": "secure123",
            "roles_codigos": "CLIENT",
        }, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        user_id = data["id"]

        # Verify UsuarioRol row has asignado_por_id set
        rows = db_session.exec(
            _select(UsuarioRol).where(UsuarioRol.usuario_id == user_id)
        ).all()
        assert len(rows) == 1
        for row in rows:
            assert row.asignado_por_id == admin_user.id, (
                f"Expected asignado_por_id={admin_user.id}, got {row.asignado_por_id}"
            )

    def test_create_user_no_roles_still_works(self, client, admin_headers, db_session):
        """Creating a user without roles should succeed without errors."""
        # Seed roles
        from app.modules.IdentidadYAcceso.Rol.models import Rol
        from sqlmodel import select as _select
        for codigo, nombre in [("ADMIN", "Admin"), ("CLIENT", "Client")]:
            if not db_session.exec(_select(Rol).where(Rol.codigo == codigo)).first():
                db_session.add(Rol(codigo=codigo, nombre=nombre))
        db_session.flush()

        response = client.post("/api/v1/usuarios/", json={
            "nombre": "NoRoles",
            "apellido": "User",
            "email": "noroles@test.com",
            "password": "secure123",
        }, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["nombre"] == "NoRoles"


class TestUsuarioUpdateAsignadoPorId:
    """PATCH /api/v1/usuarios/{id} — verify asignado_por_id is populated."""

    def test_update_user_roles_populates_asignado_por_id(self, client, admin_headers, db_session):
        """When admin reassigns roles via PATCH, UsuarioRol.asignado_por_id
        must be set to the admin's user ID."""
        from app.modules.IdentidadYAcceso.Rol.models import Rol
        from sqlmodel import select as _select
        for codigo, nombre in [("ADMIN", "Admin"), ("CLIENT", "Client"), ("PEDIDOS", "Pedidos")]:
            if not db_session.exec(_select(Rol).where(Rol.codigo == codigo)).first():
                db_session.add(Rol(codigo=codigo, nombre=nombre))
        db_session.flush()

        # Find admin user
        admin_user = db_session.exec(
            _select(Usuario).where(Usuario.email == "admin_test@test.com")
        ).first()
        assert admin_user is not None

        # Create a user first (via API to have asignado_por_id set)
        resp = client.post("/api/v1/usuarios/", json={
            "nombre": "ToUpdate",
            "apellido": "User",
            "email": "toupdate_roles@test.com",
            "password": "secure123",
            "roles_codigos": "CLIENT",
        }, headers=admin_headers)
        assert resp.status_code == 201
        user_id = resp.json()["id"]

        # PATCH: reassign role
        patch_resp = client.patch(f"/api/v1/usuarios/{user_id}", json={
            "roles_codigos": "PEDIDOS",
        }, headers=admin_headers)
        assert patch_resp.status_code == 200

        # Verify UsuarioRol rows have asignado_por_id set to admin
        rows = db_session.exec(
            _select(UsuarioRol).where(UsuarioRol.usuario_id == user_id)
        ).all()
        assert len(rows) == 1
        for row in rows:
            assert row.asignado_por_id == admin_user.id, (
                f"Expected asignado_por_id={admin_user.id}, got {row.asignado_por_id}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# ROL ENDPOINTS (ADMIN only)
# ═══════════════════════════════════════════════════════════════════════════

class TestRolEndpoints:
    """GET /api/v1/roles"""

    def test_list_roles_admin(self, client, admin_headers, db_session):
        """Admin can list roles."""
        response = client.get("/api/v1/roles/", headers=admin_headers)
        assert response.status_code == 200
        roles = response.json()
        assert isinstance(roles, list)
        assert len(roles) >= 4  # ADMIN, CLIENT, PEDIDOS, STOCK
        codigos = [r["codigo"] for r in roles]
        assert "ADMIN" in codigos
        assert "CLIENT" in codigos

    def test_get_rol_by_codigo(self, client, admin_headers, db_session):
        """Admin can get a role by code."""
        response = client.get("/api/v1/roles/ADMIN", headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["codigo"] == "ADMIN"

    def test_get_rol_not_found_returns_404(self, client, admin_headers):
        """Non-existent role code returns 404."""
        response = client.get("/api/v1/roles/NONEXISTENT", headers=admin_headers)
        assert response.status_code == 404

    def test_list_roles_client_rejected(self, client, client_headers):
        """Client cannot list roles (403)."""
        response = client.get("/api/v1/roles/", headers=client_headers)
        assert response.status_code == 403

    def test_list_roles_unauthenticated_returns_401(self, client):
        """No auth returns 401."""
        response = client.get("/api/v1/roles/")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# DIRECCION ENTREGA ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

class TestDireccionEntrega:
    """POST/GET/PATCH/DELETE /api/v1/direcciones"""

    def test_create_direccion(self, client, client_headers, db_session):
        """Authenticated user can create a delivery address."""
        response = client.post("/api/v1/direcciones/", json={
            "alias": "Casa",
            "linea1": "Calle Falsa 123",
            "ciudad": "Mendoza",
            "provincia": "Mendoza",
            "codigo_postal": "5500",
            "es_principal": True,
        }, headers=client_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["linea1"] == "Calle Falsa 123"
        assert data["es_principal"] is True

    def test_list_own_direcciones(self, client, client_headers, db_session):
        """User can list their own addresses."""
        client.post("/api/v1/direcciones/", json={
            "alias": "Casa", "linea1": "Calle 1", "ciudad": "Mendoza",
        }, headers=client_headers)
        client.post("/api/v1/direcciones/", json={
            "alias": "Trabajo", "linea1": "Calle 2", "ciudad": "Godoy Cruz",
        }, headers=client_headers)

        response = client.get("/api/v1/direcciones/", headers=client_headers)
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_direccion_isolation(self, client, client_headers, db_session):
        """User A cannot see User B's addresses."""
        # User A creates address
        client.post("/api/v1/direcciones/", json={
            "alias": "Casa A", "linea1": "User A Street", "ciudad": "City A",
        }, headers=client_headers)

        # User B creates address
        from tests.conftest import create_user_with_role
        _, headers_b = create_user_with_role(
            db_session,
            nombre="UserB", apellido="Test",
            email=f"userb_dir@test.com",
            roles_codigos="CLIENT",
        )
        client.post("/api/v1/direcciones/", json={
            "alias": "Casa B", "linea1": "User B Street", "ciudad": "City B",
        }, headers=headers_b)

        # User A sees only his addresses
        resp_a = client.get("/api/v1/direcciones/", headers=client_headers)
        for d in resp_a.json():
            assert d["linea1"] != "User B Street"

    def test_principal_management(self, client, client_headers, db_session):
        """Setting es_principal=True unsets old principal."""
        r1 = client.post("/api/v1/direcciones/", json={
            "alias": "Casa", "linea1": "Old Principal", "ciudad": "Mendoza",
            "es_principal": True,
        }, headers=client_headers)

        r2 = client.post("/api/v1/direcciones/", json={
            "alias": "Trabajo", "linea1": "New Principal", "ciudad": "Mendoza",
            "es_principal": True,
        }, headers=client_headers)

        all_addrs = client.get("/api/v1/direcciones/", headers=client_headers).json()
        principals = [d for d in all_addrs if d["es_principal"]]
        assert len(principals) == 1
        assert principals[0]["id"] == r2.json()["id"]

    def test_set_principal_endpoint(self, client, client_headers, db_session):
        """PATCH /direcciones/{id}/principal sets address as default."""
        r = client.post("/api/v1/direcciones/", json={
            "alias": "Casa", "linea1": "Test Street", "ciudad": "Mendoza",
            "es_principal": False,
        }, headers=client_headers)
        addr_id = r.json()["id"]

        resp = client.patch(
            f"/api/v1/direcciones/{addr_id}/principal",
            headers=client_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["es_principal"] is True

    def test_delete_direccion(self, client, client_headers, db_session):
        """DELETE /direcciones/{id} soft-deletes an address."""
        r = client.post("/api/v1/direcciones/", json={
            "alias": "ToDelete", "linea1": "Delete Street", "ciudad": "Mendoza",
        }, headers=client_headers)
        addr_id = r.json()["id"]

        resp = client.delete(
            f"/api/v1/direcciones/{addr_id}", headers=client_headers,
        )
        assert resp.status_code == 204

        # Verify it's gone from normal listing
        list_resp = client.get("/api/v1/direcciones/", headers=client_headers)
        remaining_ids = [d["id"] for d in list_resp.json()]
        assert addr_id not in remaining_ids

    def test_direccion_without_auth_returns_401(self, client):
        """Unauthenticated access returns 401."""
        response = client.get("/api/v1/direcciones/")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
# LOCALES (es_local) TESTS — task 4.1-4.4
# ═══════════════════════════════════════════════════════════════════════════

class TestDireccionLocales:

    def test_crear_local_como_admin(self, client, admin_headers, db_session):
        """ADMIN creates a local (es_local=true) — task 4.1."""
        from tests.conftest import _seed_roles
        _seed_roles(db_session)

        response = client.post("/api/v1/direcciones/", json={
            "alias": "Sucursal Centro",
            "linea1": "Av. San Martin 500",
            "ciudad": "Mendoza",
            "provincia": "Mendoza",
            "es_local": True,
        }, headers=admin_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["es_local"] is True
        assert data["alias"] == "Sucursal Centro"

    def test_listar_locales_cross_admin(self, client, admin_headers, db_session):
        """Admin B sees Admin A's locales when listing direcciones — task 4.2."""
        from tests.conftest import _seed_roles, _create_auth_headers
        _seed_roles(db_session)
        from app.modules.IdentidadYAcceso.Usuario.models import Usuario
        from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol
        from sqlmodel import select

        # Create Admin A's local
        response = client.post("/api/v1/direcciones/", json={
            "alias": "Sucursal Norte",
            "linea1": "Las Heras 1200",
            "ciudad": "Mendoza",
            "es_local": True,
        }, headers=admin_headers)
        assert response.status_code == 201

        # Create a second admin user
        admin_b = Usuario(
            nombre="AdminB", apellido="Test",
            email="admin_b@test.com",
            password_hash=get_password_hash("admin123"),
        )
        db_session.add(admin_b)
        db_session.flush()
        db_session.add(UsuarioRol(usuario_id=admin_b.id, rol_codigo="ADMIN"))
        db_session.flush()

        admin_b_headers = _create_auth_headers(db_session, admin_b.id, "admin_b@test.com", "ADMIN")

        # Admin B should see Admin A's local
        response2 = client.get("/api/v1/direcciones/", headers=admin_b_headers)
        assert response2.status_code == 200
        direcciones = response2.json()
        assert len(direcciones) >= 1
        locales = [d for d in direcciones if d.get("es_local")]
        assert len(locales) >= 1
        assert locales[0]["alias"] == "Sucursal Norte"

    def test_cliente_no_ve_locales_sin_incluir(self, client, client_headers, db_session):
        """CLIENT listing direcciones (without incluir_locales) does NOT see locales — task 4.3."""
        from tests.conftest import _seed_roles, create_user_with_role
        _seed_roles(db_session)

        # Create a local directly in the DB
        admin_user, _admin_h = create_user_with_role(db_session, email="admin_noloc@test.com", roles_codigos="ADMIN")
        from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega
        local = DireccionEntrega(
            usuario_id=admin_user.id,
            alias="Local DB",
            linea1="Calle DB 1",
            ciudad="Mendoza",
            es_local=True,
        )
        db_session.add(local)
        db_session.flush()

        response = client.get("/api/v1/direcciones/", headers=client_headers)
        assert response.status_code == 200
        direcciones = response.json()
        # Client should NOT see the local in their regular listing
        locales = [d for d in direcciones if d.get("es_local")]
        assert len(locales) == 0

    def test_cliente_ve_locales_con_incluir(self, client, client_headers, db_session):
        """CLIENT with incluir_locales=true sees their direcciones + locales — task 4.4."""
        from tests.conftest import _seed_roles, create_user_with_role
        _seed_roles(db_session)

        # Create a local directly in the DB
        admin_user, _admin_h = create_user_with_role(db_session, email="admin_inc@test.com", roles_codigos="ADMIN")
        from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega
        local = DireccionEntrega(
            usuario_id=admin_user.id,
            alias="Local Incluir",
            linea1="Av. Incluir 500",
            ciudad="Godoy Cruz",
            es_local=True,
        )
        db_session.add(local)
        db_session.flush()

        # CLIENT creates a personal address
        client.post("/api/v1/direcciones/", json={
            "alias": "Mi Casa",
            "linea1": "Calle Personal 42",
            "ciudad": "Mendoza",
        }, headers=client_headers)

        # With incluir_locales=true
        response = client.get("/api/v1/direcciones/?incluir_locales=true", headers=client_headers)
        assert response.status_code == 200
        direcciones = response.json()
        # Client sees their own + locales
        assert len(direcciones) >= 2
        locales = [d for d in direcciones if d.get("es_local")]
        assert len(locales) >= 1
        assert locales[0]["alias"] == "Local Incluir"

    def test_admin_no_puede_crear_pedido(self, client, admin_headers, db_session):
        """ADMIN blocked from POST /pedidos/ — task 4.5."""
        from tests.conftest import _seed_roles
        _seed_roles(db_session)
        # Need estados and formas_pago for pedido creation
        from app.modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
        from app.modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago
        from sqlmodel import select

        for codigo, desc, orden, terminal in [
            ("PENDIENTE", "Pendiente", 1, False),
            ("CONFIRMADO", "Confirmado", 2, False),
        ]:
            if not db_session.exec(select(EstadoPedido).where(EstadoPedido.codigo == codigo)).first():
                db_session.add(EstadoPedido(codigo=codigo, descripcion=desc, orden=orden, es_terminal=terminal))
        for codigo, desc, hab in [
            ("PAGO_LOCAL", "Pago local", True),
        ]:
            if not db_session.exec(select(FormaPago).where(FormaPago.codigo == codigo)).first():
                db_session.add(FormaPago(codigo=codigo, descripcion=desc, habilitado=hab))
        db_session.flush()

        response = client.post("/api/v1/pedidos/", json={
            "forma_pago_codigo": "PAGO_LOCAL",
            "subtotal": "100.00",
            "detalles": [],
        }, headers=admin_headers)
        assert response.status_code == 403
