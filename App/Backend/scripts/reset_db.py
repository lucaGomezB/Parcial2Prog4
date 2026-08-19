"""
reset_db.py  --  Destructive database reset utility (pre-Alembic).

DROPS ALL tables via schema cascade, recreates them from current SQLModel
definitions, and re-runs the seed.

WARNING: This is a DESTRUCTIVE operation. All data is permanently lost.
Use this only in local development when model definitions change and
SQLModel.metadata.create_all cannot keep up (it does NOT run ALTER TABLE).

This script predates Alembic. For production or shared environments, always
use Alembic migrations instead.

Usage:
    python scripts/reset_db.py          # prompts for confirmation
    python scripts/reset_db.py --force   # skip confirmation

Requires:
  - PostgreSQL accessible via Backend/.env
  - Backend dependencies installed
"""

import os
import sys
from pathlib import Path

# Ensure the Backend/ directory is on sys.path so module imports resolve.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session

# Import all models to populate SQLModel.metadata with every known table.
# If any model is missing here, its table will NOT be recreated.
from app.modules.CatalogoDeProductos.Categoria.models import Categoria
from app.modules.CatalogoDeProductos.Producto.models import Producto
from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from app.modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
from app.modules.IdentidadYAcceso.Rol.models import Rol
from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from app.modules.IdentidadYAcceso.RefreshToken.models import RefreshToken
from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega
from app.modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
from app.modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago
from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido
from app.modules.VentasPagosTrazabilidad.DetallePedido.models import DetallePedido
from app.modules.VentasPagosTrazabilidad.HistorialEstadoPedido.models import HistorialEstadoPedido
from app.modules.VentasPagosTrazabilidad.Pago.models import Pago


def reset_database():
    """Drop all tables, recreate them, and re-seed.

    Steps performed:
      1. Drop the entire public schema with CASCADE (removes all tables, types, FKs).
      2. Recreate the public schema and restore default privileges.
      3. Create all tables from the current SQLModel metadata.
      4. Run the seed to populate reference data.
    """
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("FATAL: DATABASE_URL not found in .env")
        sys.exit(1)

    print(f"Dropping ALL tables from: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL, echo=False)

    # --- STEP 1: Drop everything ---
    # DROP SCHEMA public CASCADE removes all objects (tables, sequences, FKs, views).
    # This is more reliable than dropping individual tables.
    with engine.connect() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        # --- STEP 2: Recreate empty schema ---
        conn.exec_driver_sql("CREATE SCHEMA public")
        # Restore default permissions so the app user can operate normally.
        conn.exec_driver_sql("GRANT ALL ON SCHEMA public TO postgres")
        conn.exec_driver_sql("GRANT ALL ON SCHEMA public TO public")
        conn.commit()
    print("All tables dropped.")

    # --- STEP 3: Recreate tables from current model definitions ---
    SQLModel.metadata.create_all(engine)
    print("All tables recreated with current schema.")

    # --- STEP 4: Re-populate with seed data ---
    print("\nRe-seeding...")
    from app.db.seed import run_seed
    run_seed()
    print("Seed complete.")

    print("\n Database reset and re-seeded successfully.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    if not force:
        confirm = input("This will DROP ALL TABLES and recreate them. Continue? (y/N): ")
        if confirm.lower() != "y":
            print("Aborted.")
            sys.exit(0)
    reset_database()
