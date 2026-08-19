"""
sprint_seed.py  —  Sprint de datos de prueba
============================================
Crea la base mínima de datos para poder desarrollar y testear el frontend
sin tener que cargar todo a mano.

    python scripts/sprint_seed.py

Requiere:
  - Backend detenido (usa la misma DB que el backend, evita locks)
  - PostgreSQL accesible con la config de Backend/.env
  - Dependencias del backend instaladas (pip install -r requirements.txt)

Tipos de datos creados:
  1. Roles          (ADMIN, STOCK, PEDIDOS, CLIENT)
  2. Usuarios       (admin, stock, pedidos, client)
  3. Categorías     (Bebidas -> Frías/Calientes, Sandwichs, etc.)
  4. Ingredientes   (Pan, Queso, Leche, etc.)
  5. Productos      (Coca Cola, Café, Hamburguesa, etc.)
"""

import os
import sys
import random
from pathlib import Path

# ── Asegurar que podemos importar los módulos del backend ──
_BACKEND_DIR = str(Path(__file__).resolve().parent.parent)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session, select
from sqlalchemy import Engine

# ── Modelos ──
from app.modules.IdentidadYAcceso.Rol.models import Rol
from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from app.modules.IdentidadYAcceso.Usuario.service import get_password_hash
from app.modules.CatalogoDeProductos.Categoria.models import Categoria
from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from app.modules.CatalogoDeProductos.Producto.models import Producto
from app.modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
from app.modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
from app.modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago

# ═══════════════════════════════════════════════════════════════
#  DATOS
# ═══════════════════════════════════════════════════════════════

ROLES = [
    Rol(codigo="ADMIN",   nombre="Administrador", descripcion="Acceso total sin restricciones"),
    Rol(codigo="STOCK",   nombre="Stock",         descripcion="Actualiza stock y disponibilidad"),
    Rol(codigo="PEDIDOS", nombre="Pedidos",       descripcion="Gestiona estados de pedido"),
    Rol(codigo="CLIENT",  nombre="Cliente",       descripcion="Opera solo con sus propios datos"),
]

USUARIOS = [
    dict(nombre="Admin",  apellido="Sistema",  email="admin@email.com",   password="admin123",   rol="ADMIN"),
    dict(nombre="Stock",  apellido="Sistema",  email="stock@email.com",   password="stock123",   rol="STOCK"),
    dict(nombre="Pedidos",apellido="Sistema",  email="pedidos@email.com", password="pedidos123", rol="PEDIDOS"),
    dict(nombre="Cliente",apellido="Estandar", email="client@email.com",  password="client123",  rol="CLIENT"),
]

CATEGORIAS = [
    # (nombre, descripción, parent_id_nombre, orden)
    ("Bebidas",       "Todas las bebidas",             None, 1),
    ("Bebidas Frías", "Gaseosas, jugos, aguas",        "Bebidas", 1),
    ("Bebidas Calientes", "Café, té, chocolate",       "Bebidas", 2),
    ("Sandwichs",     "Sandwichs fríos y calientes",   None, 2),
    ("Sandwichs Calientes", "Tostados, hamburguesas",  "Sandwichs", 1),
    ("Sandwichs Fríos", "Sandwich de miga, ciabatta",  "Sandwichs", 2),
    ("Guarniciones",  "Papas fritas, aros de cebolla", None, 3),
    ("Postres",       "Flan, helado, tortas",          None, 4),
]

INGREDIENTES = [
    ("Pan de hamburguesa",  False),
    ("Pan de miga",         False),
    ("Pan ciabatta",        False),
    ("Carne de res",        False),
    ("Pechuga de pollo",    False),
    ("Queso cheddar",       True),   # lácteo
    ("Queso mozzarella",    True),
    ("Lechuga",             False),
    ("Tomate",              False),
    ("Cebolla",             False),
    ("Huevo",               True),   # alérgeno común
    ("Mayonesa",            True),   # huevo
    ("Mostaza",             False),
    ("Ketchup",             False),
    ("Papa",                False),
    ("Aceite",              False),
    ("Sal",                 False),
    ("Café molido",         False),
    ("Leche",               True),   # lactosa
    ("Crema de leche",      True),
    ("Chocolate",           True),   # puede tener leche/soja
    ("Harina de trigo",     True),   # gluten
    ("Azúcar",              False),
    ("Hielo",               False),
    ("Gasificación",        False),
    ("Agua",                False),
    ("Levadura",            False),
    ("Manteca",             True),   # lactosa
    ("Dulce de leche",      True),
    ("Vainilla",            False),
]

PRODUCTOS = [
    # (nombre, descripción, precio, tiempo_min, disponible,
    #   categorias=[(nombre_cat, es_principal)], ingredientes=[(nombre_ing, removible, principal, orden)])
    dict(
        nombre="Coca Cola 500ml",
        descripcion="Gaseosa sabor cola",
        precio=1200.00, tiempo=1, disponible=True,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[("Agua", False, False, 1), ("Gasificación", False, False, 2),
                      ("Azúcar", False, False, 3)],
    ),
    dict(
        nombre="Café con Leche",
        descripcion="Café expreso con leche cremada",
        precio=1500.00, tiempo=5, disponible=True,
        categorias=[("Bebidas Calientes", True)],
        ingredientes=[("Café molido", False, True, 1), ("Leche", True, False, 2)],
    ),
    dict(
        nombre="Hamburguesa Clásica",
        descripcion="Medallón de res, cheddar, lechuga y tomate",
        precio=4500.00, tiempo=12, disponible=True,
        categorias=[("Sandwichs Calientes", True)],
        ingredientes=[
            ("Pan de hamburguesa", False, False, 1),
            ("Carne de res", False, True, 2),
            ("Queso cheddar", True, False, 3),
            ("Lechuga", True, False, 4),
            ("Tomate", True, False, 5),
        ],
    ),
    dict(
        nombre="Sandwich de Miga (Jamón y Queso)",
        descripcion="Triple de jamón cocido, queso y mayonesa",
        precio=2800.00, tiempo=5, disponible=True,
        categorias=[("Sandwichs Fríos", True)],
        ingredientes=[
            ("Pan de miga", False, False, 1),
            ("Queso mozzarella", False, True, 2),
            ("Mayonesa", True, False, 3),
        ],
    ),
    dict(
        nombre="Papas Fritas Grandes",
        descripcion="Porción de papas fritas crocantes",
        precio=2200.00, tiempo=8, disponible=True,
        categorias=[("Guarniciones", True)],
        ingredientes=[("Papa", False, True, 1), ("Aceite", False, False, 2), ("Sal", False, False, 3)],
    ),
    dict(
        nombre="Flan con Dulce de Leche",
        descripcion="Flan casero con dulce de leche y crema",
        precio=2500.00, tiempo=2, disponible=True,
        categorias=[("Postres", True)],
        ingredientes=[("Huevo", False, True, 1), ("Leche", False, False, 2),
                      ("Dulce de leche", True, False, 3), ("Vainilla", False, False, 4)],
    ),
]

ESTADOS_PEDIDO = [
    EstadoPedido(codigo="PENDIENTE",  descripcion="Pedido creado, pago pendiente",  orden=1, es_terminal=False),
    EstadoPedido(codigo="CONFIRMADO", descripcion="Pago procesado y confirmado",    orden=2, es_terminal=False),
    EstadoPedido(codigo="EN_PREP",    descripcion="En preparacion en cocina",        orden=3, es_terminal=False),
    EstadoPedido(codigo="ENTREGADO",  descripcion="Entrega confirmada",             orden=4, es_terminal=True),
    EstadoPedido(codigo="CANCELADO",  descripcion="Pedido cancelado",               orden=5, es_terminal=True),
]

FORMAS_PAGO = [
    FormaPago(codigo="MERCADOPAGO",   descripcion="MercadoPago",          habilitado=True),
    FormaPago(codigo="EFECTIVO",      descripcion="Efectivo",             habilitado=False),
    FormaPago(codigo="PAGO_LOCAL",    descripcion="Pago y retiro en local", habilitado=True),
    FormaPago(codigo="TRANSFERENCIA", descripcion="Transferencia",        habilitado=True),
]

# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

VERDE = "\033[92m"
AMARILLO = "\033[93m"
AZUL = "\033[94m"
ROJO = "\033[91m"
GRIS = "\033[90m"
NORMAL = "\033[0m"


def ok(msg: str):
    print(f"  [{VERDE}OK{NORMAL}] {msg}")


def skip(msg: str):
    print(f"  [{AMARILLO}-{NORMAL}] {msg}")


def create(msg: str):
    print(f"  [{AZUL}+{NORMAL}] {msg}")


def error(msg: str):
    print(f"  [{ROJO}!{NORMAL}] {msg}")


def get_or_create(session: Session, model_cls: type, filters: dict, defaults: dict = None) -> tuple:
    """
    Busca un registro por `filters`. Si no existe, lo crea con `defaults`.
    Retorna (instancia, fue_creado).
    """
    stmt = select(model_cls).filter_by(**filters)
    instance = session.exec(stmt).first()
    if instance:
        return instance, False

    creation_data = {**filters, **(defaults or {})}
    instance = model_cls(**creation_data)
    session.add(instance)
    session.flush()  # asignar ID sin commit global
    return instance, True


def get_by_name(session: Session, model_cls: type, name: str):
    """Busca una instancia por su nombre (asumiendo campo 'nombre')."""
    return session.exec(select(model_cls).where(model_cls.nombre == name)).first()

def get_engine() -> Engine:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print(f"\n{ROJO}ERROR: DATABASE_URL no está definida en Backend/.env{NORMAL}")
        sys.exit(1)
    return create_engine(db_url, echo=False)


# ═══════════════════════════════════════════════════════════════
#  SEEDERS
# ═══════════════════════════════════════════════════════════════

def seed_roles(session: Session):
    """Crea los 4 roles si no existen."""
    print(f"\n{AZUL}-- Roles --{NORMAL}")
    creados = 0
    for rol in ROLES:
        existing = session.exec(select(Rol).where(Rol.codigo == rol.codigo)).first()
        if existing:
            skip(f"{rol.codigo:<8} ya existe")
        else:
            session.add(rol)
            session.flush()
            create(f"{rol.codigo:<8} -> {rol.nombre}")
            creados += 1
    session.commit()
    if creados == 0:
        ok("Todos los roles ya estaban creados")
    else:
        ok(f"{creados} rol(es) creado(s)")


def seed_usuarios(session: Session):
    """Crea los 4 usuarios con sus roles asignados."""
    print(f"\n{AZUL}-- Usuarios --{NORMAL}")
    creados = 0
    for data in USUARIOS:
        existing = session.exec(select(Usuario).where(Usuario.email == data["email"])).first()
        if existing:
            skip(f"{data['email']:<25} ya existe")
            continue

        nuevo = Usuario(
            nombre=data["nombre"],
            apellido=data["apellido"],
            email=data["email"],
            password_hash=get_password_hash(data["password"]),
        )
        session.add(nuevo)
        session.flush()

        # Asignar rol
        rol = session.exec(select(Rol).where(Rol.codigo == data["rol"])).first()
        if rol:
            enlace = UsuarioRol(usuario_id=nuevo.id, rol_codigo=rol.codigo)
            session.add(enlace)
        else:
            error(f"Rol '{data['rol']}' no encontrado para {data['email']}")

        create(f"{data['email']:<25} / {data['password']:<10} -> {data['rol']}")
        creados += 1

    session.commit()
    if creados == 0:
        ok("Todos los usuarios ya estaban creados")
    else:
        ok(f"{creados} usuario(s) creado(s)")


def seed_categorias(session: Session):
    """Crea las categorías jerárquicas."""
    print(f"\n{AZUL}-- Categorias --{NORMAL}")
    creados = 0
    # Primera pasada: crear todas (parent=None primero)
    created: dict[str, Categoria] = {}

    for nombre, desc, parent_nombre, orden in CATEGORIAS:
        existing = get_by_name(session, Categoria, nombre)
        if existing:
            created[nombre] = existing
            skip(f"{nombre:<20} ya existe")
            continue

        cat = Categoria(nombre=nombre, descripcion=desc, orden_display=orden)
        session.add(cat)
        session.flush()
        created[nombre] = cat
        create(f"{nombre:<20} creada")
        creados += 1

    session.commit()

    # Segunda pasada: asignar padres
    for nombre, desc, parent_nombre, orden in CATEGORIAS:
        if parent_nombre:
            cat = created.get(nombre) or get_by_name(session, Categoria, nombre)
            parent = created.get(parent_nombre) or get_by_name(session, Categoria, parent_nombre)
            if cat and parent and cat.parent_id is None:
                cat.parent_id = parent.id
                session.add(cat)

    session.commit()

    if creados == 0:
        ok("Todas las categorías ya estaban creadas")
    else:
        ok(f"{creados} categoría(s) creada(s)")


def seed_ingredientes(session: Session):
    """Crea los ingredientes."""
    print(f"\n{AZUL}-- Ingredientes --{NORMAL}")
    creados = 0
    for nombre, alergeno in INGREDIENTES:
        existing = get_by_name(session, Ingrediente, nombre)
        if existing:
            skip(f"{nombre:<22} ya existe")
            continue

        ing = Ingrediente(nombre=nombre, es_alergeno=alergeno)
        session.add(ing)
        session.flush()
        alergeno_str = f"{ROJO}[alérgeno]{NORMAL}" if alergeno else f"{GRIS}no alérgeno{NORMAL}"
        create(f"{nombre:<22} -> {alergeno_str}")
        creados += 1

    session.commit()
    if creados == 0:
        ok("Todos los ingredientes ya estaban creados")
    else:
        ok(f"{creados} ingrediente(s) creado(s)")


def seed_productos(session: Session):
    """Crea los productos con sus relaciones a categorías e ingredientes."""
    print(f"\n{AZUL}-- Productos --{NORMAL}")
    creados = 0

    for prod_data in PRODUCTOS:
        existing = get_by_name(session, Producto, prod_data["nombre"])
        if existing:
            skip(f"{prod_data['nombre']:<30} ya existe")
            continue

        stock = random.randint(0, 500)
        # Regla de negocio: stock 0 → no disponible
        disponible = prod_data["disponible"] and stock > 0

        producto = Producto(
            nombre=prod_data["nombre"],
            descripcion=prod_data["descripcion"],
            precio_base=prod_data["precio"],
            stock_cantidad=stock,
            tiempo_prep_min=prod_data["tiempo"],
            disponible=disponible,
        )
        session.add(producto)
        session.flush()

        # Asignar categorías
        for cat_nombre, es_principal in prod_data["categorias"]:
            cat = get_by_name(session, Categoria, cat_nombre)
            if cat:
                session.add(ProductoCategoria(
                    producto_id=producto.id,
                    categoria_id=cat.id,
                    es_principal=es_principal,
                ))

        # Asignar ingredientes
        for ing_nombre, removible, principal, orden in prod_data["ingredientes"]:
            ing = get_by_name(session, Ingrediente, ing_nombre)
            if ing:
                session.add(ProductoIngrediente(
                    producto_id=producto.id,
                    ingrediente_id=ing.id,
                    es_removible=removible,
                    es_principal=principal,
                    orden=orden,
                ))

        create(f"{prod_data['nombre']:<30} -> ${prod_data['precio']:.2f}")
        creados += 1

    session.commit()
    if creados == 0:
        ok("Todos los productos ya estaban creados")
    else:
        ok(f"{creados} producto(s) creado(s)")


def seed_estados_pedido(session: Session):
    """Crea los 6 estados de pedido FSM si no existen (idempotente)."""
    print(f"\n{AZUL}-- Estados de Pedido --{NORMAL}")
    creados = 0
    for estado in ESTADOS_PEDIDO:
        existing = session.exec(select(EstadoPedido).where(EstadoPedido.codigo == estado.codigo)).first()
        if existing:
            skip(f"{estado.codigo:<12} ya existe")
        else:
            session.add(estado)
            session.flush()
            terminal_str = f"{ROJO}[terminal]{NORMAL}" if estado.es_terminal else f"{GRIS}[no terminal]{NORMAL}"
            create(f"{estado.codigo:<12} orden={estado.orden} {terminal_str}")
            creados += 1
    session.commit()
    if creados == 0:
        ok("Todos los estados ya estaban creados")
    else:
        ok(f"{creados} estado(s) creado(s)")


def seed_formas_pago(session: Session):
    """Crea las 3 formas de pago si no existen (idempotente)."""
    print(f"\n{AZUL}-- Formas de Pago --{NORMAL}")
    creados = 0
    for fp in FORMAS_PAGO:
        existing = session.exec(select(FormaPago).where(FormaPago.codigo == fp.codigo)).first()
        if existing:
            skip(f"{fp.codigo:<14} ya existe")
        else:
            session.add(fp)
            session.flush()
            create(f"{fp.codigo:<14} -> {fp.descripcion}")
            creados += 1
    session.commit()
    if creados == 0:
        ok("Todas las formas de pago ya estaban creadas")
    else:
        ok(f"{creados} forma(s) de pago creada(s)")


# ═══════════════════════════════════════════════════════════════
#  RESUMEN FINAL
# ═══════════════════════════════════════════════════════════════

def mostrar_resumen(session: Session):
    """Muestra counts de todo lo que hay en la DB."""
    print(f"\n{AZUL}== Resumen de la base de datos =={NORMAL}")
    totales = {
        "Roles":      session.exec(select(Rol)).all().__len__(),
        "Usuarios":   session.exec(select(Usuario)).all().__len__(),
        "Categorías": session.exec(select(Categoria)).all().__len__(),
        "Ingredientes": session.exec(select(Ingrediente)).all().__len__(),
        "Productos":  session.exec(select(Producto)).all().__len__(),
    }
    for nombre, total in totales.items():
        print(f"  - {nombre:<20} {total}")

    print(f"\n{VERDE}Usuarios disponibles:{NORMAL}")
    for u in session.exec(select(Usuario)).all():
        # Obtener roles del usuario
        roles = session.exec(
            select(Rol.codigo)
            .join(UsuarioRol, UsuarioRol.rol_codigo == Rol.codigo)
            .where(UsuarioRol.usuario_id == u.id)
        ).all()
        roles_str = ", ".join(roles) if roles else f"{ROJO}sin rol{NORMAL}"
        print(f"  - {u.email:<25} / (pass) -> {roles_str}")

    print()


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    engine = get_engine()
    print(f"""
{AZUL}+--- Sprint Seed - Datos de Prueba ---+{NORMAL}
    """)

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        seed_roles(session)
        seed_usuarios(session)
        seed_categorias(session)
        seed_ingredientes(session)
        seed_productos(session)
        seed_estados_pedido(session)
        seed_formas_pago(session)
        mostrar_resumen(session)

    print(f"{VERDE}¡Sprint completado!{NORMAL}\n")


if __name__ == "__main__":
    main()
