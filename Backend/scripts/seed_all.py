"""
seed_all.py  --  Main database seeder for development and testing.

Creates ALL seed data needed for development and testing workflows:
    Roles, Users, Categories, Ingredients, Products,
    Order States, and Payment Methods.

Idempotent: skips existing records if already present.
Can be executed with the backend running or stopped.

Usage:
    python scripts/seed_all.py

Requires:
  - PostgreSQL accessible via Backend/.env configuration
  - Backend dependencies installed

Ordering dependencies:
  Roles must be seeded before Users (FK: usuario_rol.rol_codigo).
  Users before Direcciones (FK: direccionentrega.usuario_id).
  Categories and Ingredients before Products (FKs via join tables).
"""

import os
import sys
from pathlib import Path

# Ensure the Backend/ directory is on sys.path so all module imports resolve.
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session

# Import all model classes so SQLModel.metadata is fully populated.
# Without these imports, create_all() would miss tables defined in sub-modules.
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

# Reuse the canonical seed functions from app.db.seed to keep data consistent.
from app.db.seed import (
    seed_roles,
    seed_users,
    seed_direcciones,
    seed_categorias,
    seed_ingredientes,
    seed_productos,
    seed_estados_pedido,
    seed_formas_pago,
)


# ═══════════════════════════════════════════════════════════════
#  SUMMARY DISPLAY
# ═══════════════════════════════════════════════════════════════

def mostrar_resumen(session: Session):
    """Display a row count for each entity and list users with their roles."""
    from sqlmodel import select, func

    # Count every entity type to give the developer a quick sanity check.
    totales = {
        "Roles":         session.exec(select(func.count()).select_from(Rol)).one(),
        "Usuarios":      session.exec(select(func.count()).select_from(Usuario)).one(),
        "Categorías":    session.exec(select(func.count()).select_from(Categoria)).one(),
        "Ingredientes":  session.exec(select(func.count()).select_from(Ingrediente)).one(),
        "Productos":     session.exec(select(func.count()).select_from(Producto)).one(),
        "Estados Pedido": session.exec(select(func.count()).select_from(EstadoPedido)).one(),
        "Formas Pago":   session.exec(select(func.count()).select_from(FormaPago)).one(),
    }

    print(f"\n{'='*40}")
    print("  DATABASE SEED SUMMARY")
    print(f"{'='*40}")
    for nombre, total in totales.items():
        print(f"  {nombre:<20} {total}")
    print(f"{'='*40}")

    # Print each user with their assigned roles for easy login reference.
    print(f"\n  Available users:")
    for u in session.exec(select(Usuario)).all():
        roles = session.exec(
            select(Rol.codigo)
            .join(UsuarioRol, UsuarioRol.rol_codigo == Rol.codigo)
            .where(UsuarioRol.usuario_id == u.id)
        ).all()
        roles_str = ", ".join(roles) if roles else "NO ROLE"
        print(f"    {u.email:<30} / (pass) -> {roles_str}")
    print()


# ═══════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    """Load environment, create all tables if missing, then seed every entity.

    Seed order respects foreign-key dependencies:
    roles -> users -> addresses -> categories -> ingredients -> products
    -> order states -> payment methods.
    """
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL not found in .env")
        sys.exit(1)

    print("Connecting to the database...")
    engine = create_engine(DATABASE_URL, echo=False)
    # create_all is safe to call repeatedly -- it only creates missing tables.
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Roles must come first because users depend on them via FK.
        seed_roles(session)
        seed_users(session)
        seed_direcciones(session)
        # Categories and ingredients are independent of each other but
        # both must exist before products reference them.
        seed_categorias(session)
        seed_ingredientes(session)
        seed_productos(session)
        # Order workflow entities, no further dependencies.
        seed_estados_pedido(session)
        seed_formas_pago(session)
        mostrar_resumen(session)

    print("Seed completed successfully.\n")


if __name__ == "__main__":
    main()
