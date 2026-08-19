"""
Shared test fixtures for the backend test suite.

Provides:
- engine (session-scoped): SQLite in-memory engine with StaticPool.
- db_session (function-scoped): transactional session with rollback.
- client (function-scoped): FastAPI TestClient with session override.
- Auth helpers: _create_auth_headers using real JWT tokens.
- Role-based header fixtures: admin_headers, client_headers, pedidos_headers.
- Seed fixtures: seed_roles, seed_estados_pedido, seed_formas_pago.
- Factory helpers: producto_factory, categoria_factory, ingrediente_factory,
  pedido_factory, direccion_factory.
"""
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.security.tokens import TokenData, create_access_token
from app.core.security.passwords import get_password_hash
from app.core.database import get_session

# ═══════════════════════════════════════════════════════════════════════════
# SQLITE ARRAY SUPPORT — The DetallePedido model uses Column(ARRAY(Integer)).
# SQLite does not support ARRAY type natively. This compiler hook makes
# ARRAY render as JSON string in SQLite, enabling create_all to succeed.
# ═══════════════════════════════════════════════════════════════════════════
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy import ARRAY  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
import json  # noqa: E402


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    """Render ARRAY(INTEGER) as JSON for SQLite compatibility."""
    return "JSON"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    """Render JSONB as JSON for SQLite compatibility."""
    return "JSON"


# ═══════════════════════════════════════════════════════════════════════════
# PRELOAD ALL SQLMODEL MODELS — required before create_all() to ensure
# mapper initialization resolves all cross-module relationships.
# Without these imports, SQLAlchemy mapper initialization fails with
# "expression 'Usuario' failed to locate a name" when create_all
# triggers mapper configuration for Pedido (which references Usuario).
# ═══════════════════════════════════════════════════════════════════════════
from app.modules.IdentidadYAcceso.Rol.models import Rol  # noqa: E402, F401
from app.modules.IdentidadYAcceso.Usuario.models import Usuario  # noqa: E402, F401
from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol  # noqa: E402, F401
from app.modules.IdentidadYAcceso.RefreshToken.models import RefreshToken  # noqa: E402, F401
from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega  # noqa: E402, F401
from app.modules.CatalogoDeProductos.Categoria.models import Categoria  # noqa: E402, F401
from app.modules.CatalogoDeProductos.Producto.models import Producto  # noqa: E402, F401
from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente  # noqa: E402, F401
from app.modules.CatalogoDeProductos.HistorialStock.models import HistorialStock  # noqa: E402, F401
from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida  # noqa: E402, F401
from app.modules.CatalogoDeProductos.producto_categoria import ProductoCategoria  # noqa: E402, F401
from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente  # noqa: E402, F401
from app.modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido  # noqa: E402, F401
from app.modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago  # noqa: E402, F401
from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido  # noqa: E402, F401
from app.modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido  # noqa: E402, F401
from app.modules.VentasPagosTrazabilidad.HistorialEstadoPedido.models import HistorialEstadoPedido  # noqa: E402, F401
from app.modules.VentasPagosTrazabilidad.Pago.models import Pago  # noqa: E402, F401
from app.modules.VentasPagosTrazabilidad.CarritoSnapshot.models import CarritoSnapshot  # noqa: E402, F401


# ═══════════════════════════════════════════════════════════════════════════
# Engine fixture — SQLite in-memory for fast, isolated tests
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def engine():
    """Session-scoped SQLite in-memory engine.

    Uses StaticPool so every connection gets the SAME database
    (no per-connection temporary DB). This is required because
    create_all runs on one connection and subsequent queries
    need to see those tables.

    check_same_thread=False allows SQLite to be used across
    threads (needed for TestClient's thread pool).
    """
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    yield eng
    eng.dispose()


# ═══════════════════════════════════════════════════════════════════════════
# db_session fixture — transactional, auto-rollback after each test
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="function")
def db_session(engine):
    """Function-scoped session with auto-rollback.

    Creates all tables BEFORE each test (ensures fresh schema).
    Runs inside a transaction that is rolled back AFTER each test,
    so no test can pollute another test's data.
    """
    SQLModel.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ═══════════════════════════════════════════════════════════════════════════
# client fixture — TestClient with dependency overrides
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with get_session overridden to db_session.

    Overrides the lifespan to skip Alembic migrations (which require
    a real database and alembic.ini). The db_session fixture already
    creates all tables via SQLModel.metadata.create_all().
    """
    from main import app

    # Save original lifespan and replace with no-op
    _original_lifespan = app.router.lifespan_context

    # Override the session dependency to use our test session
    def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session

    # Replace lifespan with a no-op async context manager that calls create_all
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _test_lifespan(app):
        # Tables already created by db_session fixture — no-op start
        yield
        # No-op shutdown

    # Replace lifespan on the app
    app.router.lifespan_context = _test_lifespan

    with TestClient(app) as tc:
        yield tc

    app.dependency_overrides.clear()
    app.router.lifespan_context = _original_lifespan


# ═══════════════════════════════════════════════════════════════════════════
# Auth helpers — create JWT tokens directly (bypasses rate limiter)
# ═══════════════════════════════════════════════════════════════════════════

def _create_auth_headers(
    db_session: Session,
    user_id: int,
    email: str,
    rol_codigo: str,
) -> dict[str, str]:
    """Create Authorization headers with a real JWT for the given user.

    Generates a JWT via create_access_token using the application's
    real signing key. This bypasses the login rate limiter and
    works with the actual get_current_user dependency.

    Args:
        db_session: Database session (used to ensure roles exist).
        user_id: User's database ID to encode in the JWT.
        email: User's email to encode in the JWT.
        rol_codigo: Single role code (e.g. "ADMIN"). A user can only have one role.

    Returns:
        Dict with "Authorization": "Bearer <token>".
    """
    token_data = TokenData(
        user_id=user_id,
        email=email,
        roles=[rol_codigo],
    )
    access_token = create_access_token(
        token_data,
        expires_delta=timedelta(minutes=30),
    )
    return {"Authorization": f"Bearer {access_token}"}


def create_user_with_role(
    db_session: Session,
    nombre: str = "Test",
    apellido: str = "User",
    email: str = "test@example.com",
    password: str = "test123",
    roles_codigos: str | None = None,
):
    """Create a user in the DB and return (user, auth_headers).

    Creates a real Usuario record with hashed password and a single role
    assignment via UsuarioRol. A user can only have ONE role.
    Returns both the ORM object and auth headers.
    """
    from app.modules.IdentidadYAcceso.Usuario.models import Usuario
    from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol

    if roles_codigos is None:
        roles_codigos = "CLIENT"

    user = Usuario(
        nombre=nombre,
        apellido=apellido,
        email=email,
        password_hash=get_password_hash(password),
    )
    db_session.add(user)
    db_session.flush()

    db_session.add(UsuarioRol(usuario_id=user.id, rol_codigo=roles_codigos))
    db_session.flush()

    headers = _create_auth_headers(db_session, user.id, email, roles_codigos)
    return user, headers


# ═══════════════════════════════════════════════════════════════════════════
# Seed data fixtures — reference data needed by most endpoints
# ═══════════════════════════════════════════════════════════════════════════

def _seed_roles(session: Session):
    """Ensure system roles exist in the test database."""
    from app.modules.IdentidadYAcceso.Rol.models import Rol

    ROLES = [
        ("ADMIN", "Administrador", "Acceso total sin restricciones"),
        ("STOCK", "Stock", "Actualiza stock y disponibilidad"),
        ("PEDIDOS", "Pedidos", "Gestiona estados de pedido"),
        ("CLIENT", "Cliente", "Opera solo con sus propios datos"),
    ]
    for codigo, nombre, descripcion in ROLES:
        existing = session.exec(select(Rol).where(Rol.codigo == codigo)).first()
        if not existing:
            session.add(Rol(codigo=codigo, nombre=nombre, descripcion=descripcion))
    session.flush()


def _seed_estados_pedido(session: Session):
    """Ensure order states exist in the test database."""
    from app.modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido

    ESTADOS = [
        ("PENDIENTE", "Pedido creado, pago pendiente", 1, False),
        ("CONFIRMADO", "Pago procesado y confirmado", 2, False),
        ("EN_PREP", "En preparacion en cocina", 3, False),
        ("ENTREGADO", "Entrega confirmada", 4, True),
        ("CANCELADO", "Pedido cancelado", 5, True),
    ]
    for codigo, descripcion, orden, terminal in ESTADOS:
        existing = session.exec(
            select(EstadoPedido).where(EstadoPedido.codigo == codigo)
        ).first()
        if not existing:
            session.add(EstadoPedido(
                codigo=codigo,
                descripcion=descripcion,
                orden=orden,
                es_terminal=terminal,
            ))
    session.flush()


def _seed_formas_pago(session: Session):
    """Ensure payment methods exist in the test database."""
    from app.modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago

    FORMAS = [
        ("MERCADOPAGO", "MercadoPago", True),
        ("EFECTIVO", "Efectivo", False),
        ("PAGO_LOCAL", "Pago y retiro en local", True),
        ("TRANSFERENCIA", "Transferencia", True),
    ]
    for codigo, descripcion, habilitado in FORMAS:
        existing = session.exec(
            select(FormaPago).where(FormaPago.codigo == codigo)
        ).first()
        if not existing:
            session.add(FormaPago(
                codigo=codigo,
                descripcion=descripcion,
                habilitado=habilitado,
            ))
    session.flush()


# ═══════════════════════════════════════════════════════════════════════════
# Role-based auth header fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="function")
def admin_headers(db_session):
    """Auth headers for a user with ADMIN role.

    Creates an admin user with ADMIN role and returns Bearer auth headers.
    """
    _seed_roles(db_session)
    _, headers = create_user_with_role(
        db_session,
        nombre="Admin",
        apellido="Test",
        email="admin_test@test.com",
        roles_codigos="ADMIN",
    )
    return headers


@pytest.fixture(scope="function")
def client_headers(db_session):
    """Auth headers for a user with CLIENT role.

    Creates a client user with CLIENT role and returns Bearer auth headers.
    """
    _seed_roles(db_session)
    _, headers = create_user_with_role(
        db_session,
        nombre="Client",
        apellido="Test",
        email="client_test@test.com",
        roles_codigos="CLIENT",
    )
    return headers


@pytest.fixture(scope="function")
def pedidos_headers(db_session):
    """Auth headers for a user with PEDIDOS role.

    Creates a pedidos user with PEDIDOS role and returns Bearer auth headers.
    """
    _seed_roles(db_session)
    _, headers = create_user_with_role(
        db_session,
        nombre="Pedidos",
        apellido="Test",
        email="pedidos_test@test.com",
        roles_codigos="PEDIDOS",
    )
    return headers


# ═══════════════════════════════════════════════════════════════════════════
# Factory helpers — create test entities quickly
# ═══════════════════════════════════════════════════════════════════════════

def categoria_factory(db_session: Session, **kwargs):
    """Create a Categoria for testing. Returns the ORM object.

    Default values can be overridden via kwargs.
    """
    from app.modules.CatalogoDeProductos.Categoria.models import Categoria

    defaults = {
        "nombre": "Test Category",
        "descripcion": "A test category",
        "orden_display": 1,
    }
    defaults.update(kwargs)
    cat = Categoria(**defaults)
    db_session.add(cat)
    db_session.flush()
    return cat


def ingrediente_factory(db_session: Session, **kwargs):
    """Create an Ingrediente for testing. Returns the ORM object."""
    from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente

    defaults = {
        "nombre": "Test Ingredient",
        "descripcion": "A test ingredient",
        "es_alergeno": False,
        "precio_actual": Decimal("100.00"),
        "stock_actual": 50,
    }
    defaults.update(kwargs)
    ing = Ingrediente(**defaults)
    db_session.add(ing)
    db_session.flush()
    return ing


def producto_factory(db_session: Session, **kwargs):
    """Create a Producto for testing. Returns the ORM object.

    By default creates a regular (made-to-order) product with
    es_producto_terminado=False. If stock_manual is provided,
    automatically sets es_producto_terminado=True (finished/resale product).

    Accepts optional ingredientes_data: list of dicts with
    {ingrediente_id, cantidad, es_removible, es_principal, orden, unidad_medida_id}.
    Each dict creates a ProductoIngrediente association.
    """
    from app.modules.CatalogoDeProductos.Producto.models import Producto
    from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

    # Extract ingredient data before passing kwargs to Producto constructor
    ingredientes_data = kwargs.pop("ingredientes_data", [])

    defaults = {
        "nombre": "Test Product",
        "descripcion": "A test product",
        "precio_base": Decimal("500.00"),
        "precio_actual": Decimal("500.00"),
        "tiempo_prep_min": 10,
        "disponible": True,
        "es_producto_terminado": False,
    }
    defaults.update(kwargs)

    # Auto-set es_producto_terminado=True when stock_manual is provided
    if "stock_manual" in defaults and not defaults.get("es_producto_terminado"):
        defaults["es_producto_terminado"] = True

    prod = Producto(**defaults)
    db_session.add(prod)
    db_session.flush()

    # Create ingredient associations if provided
    for ing_data in ingredientes_data:
        db_session.add(ProductoIngrediente(
            producto_id=prod.id,
            ingrediente_id=ing_data["ingrediente_id"],
            cantidad=Decimal(str(ing_data.get("cantidad", 1))),
            es_removible=ing_data.get("es_removible", False),
            es_principal=ing_data.get("es_principal", False),
            orden=ing_data.get("orden", 0),
            unidad_medida_id=ing_data.get("unidad_medida_id"),
        ))
    if ingredientes_data:
        db_session.flush()

    return prod


def producto_terminado_factory(db_session: Session, **kwargs):
    """Create a finished-product (es_producto_terminado=True) for testing.
    Uses stock_manual for inventory. Returns the ORM object."""
    from app.modules.CatalogoDeProductos.Producto.models import Producto

    defaults = {
        "nombre": "Test Finished Product",
        "descripcion": "A finished/resale product",
        "precio_base": Decimal("500.00"),
        "precio_actual": Decimal("500.00"),
        "stock_manual": 100,
        "tiempo_prep_min": 0,
        "disponible": True,
        "es_producto_terminado": True,
    }
    defaults.update(kwargs)
    prod = Producto(**defaults)
    db_session.add(prod)
    db_session.flush()
    return prod


def direccion_factory(db_session: Session, usuario_id: int, **kwargs):
    """Create a DireccionEntrega for testing. Returns the ORM object."""
    from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega

    defaults = {
        "usuario_id": usuario_id,
        "alias": "Casa",
        "linea1": "Calle Test 123",
        "ciudad": "Test City",
        "provincia": "Test Province",
        "codigo_postal": "5500",
        "es_principal": False,
    }
    defaults.update(kwargs)
    dire = DireccionEntrega(**defaults)
    db_session.add(dire)
    db_session.flush()
    return dire


def pedido_factory(db_session: Session, usuario_id: int, **kwargs):
    """Create a Pedido for testing. Returns the ORM object.

    Does NOT create details or history — those are separate concerns.
    """
    from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido

    defaults = {
        "usuario_id": usuario_id,
        "estado_codigo": "PENDIENTE",
        "forma_pago_codigo": "PAGO_LOCAL",
        "subtotal": Decimal("500.00"),
        "descuento": Decimal("0.00"),
        "costo_envio": Decimal("0.00"),
        "total": Decimal("500.00"),
    }
    defaults.update(kwargs)
    ped = Pedido(**defaults)
    db_session.add(ped)
    db_session.flush()
    return ped
