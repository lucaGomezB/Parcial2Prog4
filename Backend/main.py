"""
FastAPI application factory module.

Implements the application lifespan pattern for managing startup and shutdown
lifecycle events. The lifespan context manager handles Alembic migrations,
database seeding, and cleanup tasks automatically when the app starts.

Uses a single global SQLModel engine created from DATABASE_URL environment
variable. Router inclusion follows a modular architecture where each domain
module exposes its own APIRouter.
"""

import logging
import os
from decimal import Decimal
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlmodel import create_engine, Session
from alembic.config import Config
from alembic import command
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

# Load environment variables and create the global SQLModel engine
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)


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

    Returns a 429 Too Many Requests response with a user-friendly message
    in Spanish and a Retry-After header indicating 60 seconds.
    """
    from fastapi.responses import JSONResponse
    response = JSONResponse(
        status_code=429,
        content={"detail": "Error: Demasiados intentos fallidos. Por favor vuelva a intentar en unos minutos."},
    )
    response.headers["Retry-After"] = "60"
    return response


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# CORS middleware: allows all origins for development.
# In production, restrict allow_origins to specific frontend domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
app.include_router(forma_pago_router)
app.include_router(pedido_router)


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
    return JSONResponse(
        status_code=400,
        content={"detail": "Error de integridad en la base de datos (Ej: ID inexistente o duplicado)."},
    )
