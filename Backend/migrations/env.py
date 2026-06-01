"""
migrations/env.py  --  Alembic migration environment configuration.

This module configures the Alembic migration context for both online
(connected to the database) and offline (SQL script generation) modes.

It imports all SQLModel models so that Alembic can detect schema changes
by comparing target_metadata against the actual database state.
"""

import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv
import os

# Add Backend/ to sys.path so Alembic can resolve our model imports.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load environment variables from the project's .env file.
load_dotenv()

# Alembic Config object, which provides access to alembic.ini values.
config = context.config
# Override the sqlalchemy.url from alembic.ini with the value from .env.
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# Set up Python logging from the alembic.ini [loggers] section, if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so SQLModel.metadata is fully populated.
# Without these imports, Alembic auto-detection would only see a subset of tables.
from sqlmodel import SQLModel
from modules.CatalogoDeProductos.Categoria.models import Categoria
from modules.CatalogoDeProductos.Producto.models import Producto
from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
from modules.IdentidadYAcceso.Rol.models import Rol
from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
from modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega
from modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
from modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago
from modules.VentasPagosTrazabilidad.Pedido.models import Pedido
from modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
from modules.VentasPagosTrazabilidad.HistorialEstadoPedido.models import HistorialEstadoPedido
from modules.VentasPagosTrazabilidad.Pago.models import Pago

# The combined metadata from all SQLModel models.
# Alembic uses this as the source of truth to detect differences with the DB.
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Generate migration SQL scripts without connecting to the database.

    Useful for code review, CI checks, or when the DBA needs to review
    the raw SQL before applying it to a production database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the live database and apply migrations directly.

    Uses NullPool so that connections are not held open between migrations,
    which is the standard Alembic recommendation for migration scripts.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


# Alembic automatically sets is_offline_mode when --sql flag is passed.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
