"""
FastAPI application factory module.

Implements the application lifespan pattern for managing startup and shutdown
lifecycle events. The lifespan context manager handles Alembic migrations,
database seeding, and cleanup tasks automatically when the app starts.

The single global SQLModel engine lives in core.database and is imported here.
Router inclusion follows a modular architecture where each domain module
exposes its own APIRouter.
"""

import asyncio
import logging
import os
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from contextlib import asynccontextmanager

# Configure root logger so startup messages are visible during debugging.
# Without this, the lifespan error messages are swallowed silently.
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-5.5s [%(name)s] %(message)s",
)

logger = logging.getLogger("app.startup")
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, DataError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.exceptions import RequestValidationError
from app.core.problem_response import problem_response
from sqlmodel import Session
from alembic.config import Config
from alembic import command
from app.core.database import engine
from app.core.rate_limit import limiter
from app.modules.CatalogoDeProductos.Categoria.router import router as categoria_router
from app.modules.CatalogoDeProductos.Producto.router import router as producto_router
from app.modules.CatalogoDeProductos.Ingrediente.router import router as ingrediente_router
from app.modules.CatalogoDeProductos.UnidadMedida.router import router as unidad_medida_router
from app.modules.CatalogoDeProductos.HistorialStock.router import router as historial_stock_router
from app.modules.CatalogoDeProductos.stock_ws_router import stock_ws_router
from app.modules.IdentidadYAcceso.Auth.router import router as auth_router
from app.modules.IdentidadYAcceso.Usuario.router import router as usuario_router
from app.modules.IdentidadYAcceso.Rol.router import router as rol_router
from app.modules.IdentidadYAcceso.DireccionEntrega.router import router as direccion_router
from app.modules.VentasPagosTrazabilidad.FormaPago.router import router as forma_pago_router
from app.modules.VentasPagosTrazabilidad.Pedido.router import router as pedido_router
from app.modules.VentasPagosTrazabilidad.EstadoPedido.router import router as estado_pedido_router
from app.modules.VentasPagosTrazabilidad.HistorialEstadoPedido.router import router as historial_estado_router
from app.modules.VentasPagosTrazabilidad.Pago.router import router as pago_router
from app.modules.Uploads.router import router as uploads_router
from app.modules.Estadisticas.router import router as estadisticas_router
from app.modules.CatalogoDeProductos.Categoria.models import Categoria
from app.modules.CatalogoDeProductos.Producto.models import Producto
from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from app.modules.CatalogoDeProductos.HistorialStock.models import HistorialStock
from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
from app.modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
from app.modules.IdentidadYAcceso.Rol.models import Rol
from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from app.modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega
from app.modules.IdentidadYAcceso.Auth.service import cleanup_expired_tokens
from app.modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
from app.modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago
from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido
from app.modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
from app.modules.VentasPagosTrazabilidad.HistorialEstadoPedido.models import HistorialEstadoPedido
from app.modules.VentasPagosTrazabilidad.Pago.models import Pago
from app.modules.VentasPagosTrazabilidad.CarritoSnapshot.models import CarritoSnapshot

async def _cleanup_expired_snapshots():
    """Background task: delete expired cart_snapshot rows every 5 minutes."""
    logger = logging.getLogger("cart_snapshot.cleanup")
    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes
            with Session(engine) as session:
                from app.modules.VentasPagosTrazabilidad.CarritoSnapshot.repository import (
                    CarritoSnapshotRepository,
                )
                repo = CarritoSnapshotRepository(session)
                deleted = repo.delete_expired()
                if deleted > 0:
                    session.commit()
                    logger.info("Deleted %d expired cart snapshots", deleted)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Snapshot cleanup error: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    On startup:
    1. Detects whether the database is fresh (no core tables exist).
       - Fresh DB: creates schema from SQLModel metadata, seeds, stamps head.
       - Existing DB: runs alembic migrations, then idempotent seed.
    2. Cleans up any expired refresh tokens left from previous sessions.

    On shutdown: currently a no-op, but can be extended for connection pool
    cleanup or graceful worker shutdown.
    """
    # --- Startup ---
    _snapshot_cleanup_task = None
    try:
        alembic_cfg = Config("alembic.ini")
        # Override the database URL from the environment so Alembic connects
        # to the correct host (e.g., "db" in Docker instead of "localhost").
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            alembic_cfg.set_main_option("sqlalchemy.url", database_url)

        # Detect whether this is a brand-new (empty) database.
        # On a fresh DB the core tables don't exist yet, so alembic
        # incremental migrations would fail with "relation does not exist".
        # Strategy:
        #   Fresh DB  → create_all + seed + stamp(head)  (skip alembic)
        #   Existing  → alembic upgrade + seed idempotent
        from sqlmodel import text as sql_text
        with engine.connect() as conn:
            result = conn.execute(
                sql_text(
                    "SELECT EXISTS ("
                    "  SELECT FROM information_schema.tables "
                    "  WHERE table_schema = 'public' AND table_name = 'producto'"
                    ")"
                )
            )
            has_core_tables = result.scalar()

        if not has_core_tables:
            logger.info("Fresh database detected — creating schema from models")
            from app.db.seed import run_seed
            run_seed(fresh=True)
            logger.info("Schema created and seed completed")
        else:
            logger.info("Running Alembic migrations...")
            command.upgrade(alembic_cfg, "head")
            logger.info("Alembic migrations completed")

            logger.info("Running database seed...")
            from app.db.seed import run_seed
            run_seed(fresh=False)
            logger.info("Database seed completed")

        # Cleanup expired refresh tokens to prevent DB bloat
        with Session(engine) as session:
            cleanup_expired_tokens(session)

        # Start snapshot cleanup background task (runs every 5 minutes)
        _snapshot_cleanup_task = asyncio.create_task(_cleanup_expired_snapshots())

        logger.info("Application startup complete")
    except Exception as exc:
        logger.critical("FATAL: Application startup failed: %s", exc)
        logger.critical(traceback.format_exc())
        # Force-flush stderr so the error message is visible before
        # the process terminates.  Without this, uvicorn may kill the
        # process before buffered log messages are written.
        import sys
        sys.stderr.flush()
        raise

    yield  # Application runs here — between startup and shutdown

    # --- Shutdown ---
    if _snapshot_cleanup_task is not None:
        _snapshot_cleanup_task.cancel()
        try:
            await _snapshot_cleanup_task
        except asyncio.CancelledError:
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
    and a Retry-After header reflecting the actual remaining window.
    """
    retry_seconds = int(exc.retry_after) if getattr(exc, "retry_after", None) else 900
    resp = problem_response(
        status=429,
        title="Demasiados intentos",
        detail=f"Error: Demasiados intentos fallidos. Por favor vuelva a intentar en {retry_seconds} segundos.",
        instance=str(request.url),
    )
    resp.headers["Retry-After"] = str(retry_seconds)
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

# ── Request timing middleware ───────────────────────────────────────────
@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    """Log every HTTP request with method, path, status, and elapsed time."""
    start = datetime.now(timezone.utc)
    response = await call_next(request)
    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    print(f"  [{request.method}] {request.url.path} -> {response.status_code} ({elapsed_ms:.0f}ms)")
    return response

# Include all domain routers under the /api/v1 prefix
# Identity & Access module
app.include_router(auth_router, prefix="/api/v1")
app.include_router(usuario_router, prefix="/api/v1")
app.include_router(rol_router, prefix="/api/v1")
app.include_router(direccion_router, prefix="/api/v1")

# Product Catalog module
app.include_router(categoria_router, prefix="/api/v1")
app.include_router(producto_router, prefix="/api/v1")
app.include_router(ingrediente_router, prefix="/api/v1")
app.include_router(unidad_medida_router, prefix="/api/v1")
app.include_router(historial_stock_router, prefix="")
app.include_router(stock_ws_router, prefix="/api/v1/stock")

# Sales, Payments & Tracking module
app.include_router(estado_pedido_router, prefix="/api/v1")
app.include_router(forma_pago_router, prefix="/api/v1")
app.include_router(pedido_router, prefix="/api/v1")
app.include_router(historial_estado_router, prefix="/api/v1")
app.include_router(pago_router, prefix="/api/v1")

# Uploads module
app.include_router(uploads_router, prefix="/api/v1")

# Estadisticas module (analytics dashboard)
app.include_router(estadisticas_router, prefix="/api/v1")

# ── MercadoPago IPN webhook: MUST stay at /pagos/webhook with NO API prefix ──
# MP calls this path directly; adding /api/v1 would break the integration.
from app.modules.VentasPagosTrazabilidad.Pago.router import webhook_receiver
app.add_api_route("/pagos/webhook", webhook_receiver, methods=["POST"])


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


@app.exception_handler(DataError)
async def data_error_handler(request: Request, exc: DataError):
    """
    Global handler for SQLAlchemy DataError exceptions.

    Catches data-related errors (string too long, numeric overflow, etc.)
    and returns a user-friendly 400 Bad Request response instead of a
    raw database error traceback.
    """
    logger.error("DataError en %s %s: %s", request.method, request.url.path, exc)
    return problem_response(
        status=400,
        title="Error de datos",
        detail="Error de datos en la base de datos (por ejemplo: valor demasiado largo para el campo).",
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
