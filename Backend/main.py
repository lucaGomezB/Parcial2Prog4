"""
FastAPI application factory module.

Implements the application lifespan pattern for managing startup and shutdown
lifecycle events. The lifespan context manager handles Alembic migrations,
database seeding, and cleanup tasks automatically when the app starts.

The single global SQLModel engine lives in core.database and is imported here.
Router inclusion follows a modular architecture where each domain module
exposes its own APIRouter.
"""

import os
import logging
from decimal import Decimal
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.exceptions import RequestValidationError
from core.problem_response import problem_response
from sqlmodel import Session
from alembic.config import Config
from alembic import command
from core.database import engine
from core.rate_limit import limiter
from modules.CatalogoDeProductos.Categoria.router import router as categoria_router
from modules.CatalogoDeProductos.Producto.router import router as producto_router
from modules.CatalogoDeProductos.Ingrediente.router import router as ingrediente_router
from modules.IdentidadYAcceso.Auth.router import router as auth_router
from modules.IdentidadYAcceso.Usuario.router import router as usuario_router
from modules.IdentidadYAcceso.Rol.router import router as rol_router
from modules.IdentidadYAcceso.DireccionEntrega.router import router as direccion_router
from modules.VentasPagosTrazabilidad.FormaPago.router import router as forma_pago_router
from modules.VentasPagosTrazabilidad.Pedido.router import router as pedido_router
from modules.VentasPagosTrazabilidad.EstadoPedido.router import router as estado_pedido_router
from modules.VentasPagosTrazabilidad.HistorialEstadoPedido.router import router as historial_estado_router
from modules.VentasPagosTrazabilidad.Pago.router import router as pago_router
from modules.CatalogoDeProductos.Categoria.models import Categoria
from modules.CatalogoDeProductos.Producto.models import Producto
from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
from modules.IdentidadYAcceso.Rol.models import Rol
from modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
from modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega
from modules.IdentidadYAcceso.Auth.service import cleanup_expired_tokens
from modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
from modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago
from modules.VentasPagosTrazabilidad.Pedido.models import Pedido
from modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
from modules.VentasPagosTrazabilidad.HistorialEstadoPedido.models import HistorialEstadoPedido
from modules.VentasPagosTrazabilidad.Pago.models import Pago

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    On startup:
    1. Runs Alembic migrations to bring the database schema up to date.
    2. Seeds initial data (roles, users, products, etc.) in an idempotent manner.
    3. Cleans up any expired refresh tokens left from previous sessions.

    On shutdown: currently a no-op, but can be extended for connection pool
    cleanup or graceful worker shutdown.
    """
    # --- Startup ---
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    # Seed roles, users, products, and other reference data (idempotent)
    from app.db.seed import run_seed
    run_seed()

    # Cleanup expired refresh tokens to prevent DB bloat
    with Session(engine) as session:
        cleanup_expired_tokens(session)

    yield  # Application runs here — between startup and shutdown

    # --- Shutdown ---
    pass


# Initialize the FastAPI application with the lifespan manager
app = FastAPI(
    title="Sistema de Pedidos API",
    lifespan=lifespan,
    redirect_slashes=False,
    json_encoders={Decimal: float},
)

# Attach rate limiter to app state (Slowapi integration)
app.state.limiter = limiter


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom exception handler for rate limit exceeded errors.

    Returns a 429 Too Many Requests response with RFC 7807 Problem Details
    and a Retry-After header indicating 900 seconds.
    """
    resp = problem_response(
        status=429,
        title="Demasiados intentos",
        detail="Error: Demasiados intentos fallidos. Por favor vuelva a intentar en unos minutos.",
        instance=str(request.url),
    )
    resp.headers["Retry-After"] = "900"
    return resp


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# CORS middleware: use explicit origins to allow credentials.
# Reads FRONTEND_URL from .env (e.g., http://localhost:5173).
cors_origins_str = os.getenv("CORS_ORIGINS", os.getenv("FRONTEND_URL", ""))
cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()] if cors_origins_str else []

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=bool(cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all domain routers under their respective prefixes
# Identity & Access module
app.include_router(auth_router)
app.include_router(usuario_router)
app.include_router(rol_router)
app.include_router(direccion_router)

# Product Catalog module
app.include_router(categoria_router)
app.include_router(producto_router)
app.include_router(ingrediente_router)

# Sales, Payments & Tracking module
app.include_router(estado_pedido_router)
app.include_router(forma_pago_router)
app.include_router(pedido_router)
app.include_router(historial_estado_router)
app.include_router(pago_router)


@app.get("/")
def read_root():
    """Health check endpoint — returns status online if the app is running."""
    return {"status": "online"}


logger = logging.getLogger(__name__)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """
    Global handler for SQLAlchemy IntegrityError exceptions.

    Catches constraint violations (duplicate keys, FK violations, etc.)
    and returns a user-friendly 400 Bad Request response instead of a
    raw database error traceback.
    """
    logger.error("IntegrityError en %s %s: %s", request.method, request.url.path, exc)
    return problem_response(
        status=400,
        title="Error de integridad",
        detail="Error de integridad en la base de datos (Ej: ID inexistente o duplicado).",
        instance=str(request.url),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Global handler for HTTPException that formats responses using RFC 7807.

    Extracts structured information from the exception detail when possible.
    """
    detail = exc.detail
    title = "Error de solicitud"

    # Si detail es un dict, extraer informacion estructurada
    extra = None
    if isinstance(detail, dict):
        title = detail.get("mensaje", detail.get("error", "Error de solicitud"))
        extra = {k: v for k, v in detail.items() if k not in ("mensaje",)}
        detail = detail.get("mensaje", detail.get("error", "Error de solicitud"))

    return problem_response(
        status=exc.status_code,
        title=title,
        detail=str(detail) if not isinstance(detail, str) else detail,
        instance=str(request.url),
        extra=extra,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Global handler for Pydantic validation errors (422).

    Formats the response using RFC 7807 with detailed validation error information.
    """
    return problem_response(
        status=422,
        title="Error de validacion",
        detail="Los datos enviados no son validos",
        instance=str(request.url),
        extra={"errors": exc.errors()},
    )
