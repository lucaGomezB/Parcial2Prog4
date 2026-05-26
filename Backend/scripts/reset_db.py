"""
Reset the database: DROP ALL tables, recreate from current models, re-seed.

Run this when model definitions change and columns are missing in PostgreSQL
(SQLModel.metadata.create_all does NOT alter existing tables).

Usage:
    python scripts/reset_db.py
"""
import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so we can import backend modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session

# ── Load all models so SQLModel.metadata knows every table ──
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


def reset_database():
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("FATAL: DATABASE_URL not found in .env")
        sys.exit(1)

    print(f"Dropping ALL tables from: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL, echo=False)

    # Drop all tables using CASCADE to handle FK dependencies
    with engine.connect() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")
        conn.exec_driver_sql("GRANT ALL ON SCHEMA public TO postgres")
        conn.exec_driver_sql("GRANT ALL ON SCHEMA public TO public")
        conn.commit()
    print("✓ All tables dropped.")

    # Recreate all tables with current schema
    SQLModel.metadata.create_all(engine)
    print("✓ All tables recreated with current schema.")

    # Re-seed
    print("\nRe-seeding...")
    from app.db.seed import run_seed
    run_seed()
    print("✓ Seed complete.")

    print("\n✅ Database reset and re-seeded successfully.")


if __name__ == "__main__":
    force = "--force" in sys.argv
    if not force:
        confirm = input("This will DROP ALL TABLES and recreate them. Continue? (y/N): ")
        if confirm.lower() != "y":
            print("Aborted.")
            sys.exit(0)
    reset_database()
