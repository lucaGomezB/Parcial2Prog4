import logging
import os
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
from modules.VentasPagosTrazabilidad.EstadoPedido.router import router as estado_pedido_router
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

# 1. Carga de entorno y configuración
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)

# 2. Definición del Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    # Seed roles (idempotente)
    from app.db.seed import run_seed
    run_seed()

    # Cleanup expired refresh tokens on startup
    with Session(engine) as session:
        cleanup_expired_tokens(session)

    yield  # Acá vive la app.

    # --- Shutdown ---
    pass


# 3. Inicialización de la App con lifespan
app = FastAPI(
    title="Sistema de Pedidos API",
    lifespan=lifespan,
    redirect_slashes=False
)

# Rate limiting
app.state.limiter = limiter

async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    from fastapi.responses import JSONResponse
    response = JSONResponse(
        status_code=429,
        content={"detail": "Error: Demasiados intentos fallidos. Por favor vuelva a intentar en unos minutos."},
    )
    response.headers["Retry-After"] = "60"
    return response

app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(usuario_router)
app.include_router(rol_router)
app.include_router(direccion_router)
app.include_router(categoria_router)
app.include_router(producto_router)
app.include_router(ingrediente_router)
app.include_router(estado_pedido_router)
app.include_router(forma_pago_router)
app.include_router(pedido_router)

@app.get("/")
def read_root():
    return {"status": "online"} # Endpoint para probar si anda la app.

logger = logging.getLogger(__name__)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.error("IntegrityError en %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=400,
        content={"detail": "Error de integridad en la base de datos (Ej: ID inexistente o duplicado)."},
    )