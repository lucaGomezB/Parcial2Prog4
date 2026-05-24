import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, create_engine, Session
from modules.CatalogoDeProductos.Categoria.router import router as categoria_router
from modules.CatalogoDeProductos.Producto.router import router as producto_router
from modules.CatalogoDeProductos.Ingrediente.router import router as ingrediente_router
from modules.IdentidadYAcceso.Auth.router import router as auth_router
from modules.IdentidadYAcceso.Usuario.router import router as usuario_router
from modules.IdentidadYAcceso.Rol.router import router as rol_router
from modules.CatalogoDeProductos.Categoria.models import Categoria
from modules.CatalogoDeProductos.Producto.models import Producto
from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
from modules.IdentidadYAcceso.Rol.models import Rol
from modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
from modules.IdentidadYAcceso.Auth.service import cleanup_expired_tokens

# 1. Carga de entorno y configuración
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=True)

# 2. Definición del Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    SQLModel.metadata.create_all(engine)  # Creación de tablas

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
app.include_router(categoria_router)
app.include_router(producto_router)
app.include_router(ingrediente_router)

@app.get("/")
def read_root():
    return {"status": "online"} # Endpoint para probar si anda la app.

@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=400,
        content={"detail": "Error de integridad en la base de datos (Ej: ID inexistente o duplicado)."},
    )