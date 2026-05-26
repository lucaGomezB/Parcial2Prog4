"""
seed_all.py  —  Seed completo de la base de datos
==================================================
Crea TODOS los datos necesarios para desarrollar y testear:

    Roles, Usuarios, Categorías, Ingredientes, Productos,
    Estados de Pedido y Formas de Pago.

Idempotente: si un registro ya existe, lo saltea.
Se puede ejecutar con el backend detenido o en funcionamiento.

Uso:
    python scripts/seed_all.py

Requiere:
  - PostgreSQL accesible con la config de Backend/.env
  - Dependencias del backend instaladas
"""
import os
import sys
from pathlib import Path

# Agregar Backend/ al sys.path
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session

# ── Todos los imports necesarios para que SQLModel.metadata esté completo ──
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

# ── Reutilizamos las funciones del seed oficial ──
from app.db.seed import (
    seed_roles,
    seed_users,
    seed_categorias,
    seed_ingredientes,
    seed_productos,
    seed_estados_pedido,
    seed_formas_pago,
)


# ═══════════════════════════════════════════════════════════════
#  RESUMEN
# ═══════════════════════════════════════════════════════════════

def mostrar_resumen(session: Session):
    """Muestra conteo de cada entidad en la BD."""
    from sqlmodel import select, func

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
    print("  RESUMEN DE LA BASE DE DATOS")
    print(f"{'='*40}")
    for nombre, total in totales.items():
        print(f"  {nombre:<20} {total}")
    print(f"{'='*40}")

    print(f"\n  Usuarios disponibles:")
    for u in session.exec(select(Usuario)).all():
        roles = session.exec(
            select(Rol.codigo)
            .join(UsuarioRol, UsuarioRol.rol_codigo == Rol.codigo)
            .where(UsuarioRol.usuario_id == u.id)
        ).all()
        roles_str = ", ".join(roles) if roles else "SIN ROL"
        print(f"    {u.email:<30} / (pass) -> {roles_str}")
    print()


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL no encontrada en .env")
        sys.exit(1)

    print("Conectando a la base de datos...")
    engine = create_engine(DATABASE_URL, echo=False)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        seed_roles(session)
        seed_users(session)
        seed_categorias(session)
        seed_ingredientes(session)
        seed_productos(session)
        seed_estados_pedido(session)
        seed_formas_pago(session)
        mostrar_resumen(session)

    print("Seed completado exitosamente.\n")


if __name__ == "__main__":
    main()
