"""
seed.py — Seed de datos para el backend.
Corre en el startup (lifespan de main.py) y también es invocable como script.

Idempotente: si un registro ya existe, lo saltea.
"""
import os
import random
from decimal import Decimal
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session, select

# ── Roles & Auth ──
from modules.IdentidadYAcceso.Rol.models import Rol
from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from modules.IdentidadYAcceso.Usuario.service import get_password_hash

# ── Catálogo ──
from modules.CatalogoDeProductos.Categoria.models import Categoria
from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from modules.CatalogoDeProductos.Producto.models import Producto, ProductoMedida
from modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente

# ── Ventas ──
from modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
from modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


# ═══════════════════════════════════════════════════════════════
#  DATA
# ═══════════════════════════════════════════════════════════════

ROLES_SEED = [
    Rol(codigo="ADMIN",   nombre="Administrador", descripcion="Acceso total sin restricciones"),
    Rol(codigo="STOCK",   nombre="Stock",         descripcion="Actualiza stock y disponibilidad"),
    Rol(codigo="PEDIDOS", nombre="Pedidos",       descripcion="Gestiona estados de pedido"),
    Rol(codigo="CLIENT",  nombre="Cliente",       descripcion="Opera solo con sus propios datos"),
]

USERS_SEED = [
    {"nombre": "Admin",   "apellido": "Sistema",  "email": "admin@email.com",   "password": "admin123",   "rol_codigo": "ADMIN"},
    {"nombre": "Stock",   "apellido": "Sistema",  "email": "stock@email.com",   "password": "stock123",   "rol_codigo": "STOCK"},
    {"nombre": "Pedidos", "apellido": "Sistema",  "email": "pedidos@email.com", "password": "pedidos123", "rol_codigo": "PEDIDOS"},
    {"nombre": "Cliente", "apellido": "Estandar", "email": "client@email.com",  "password": "client123",  "rol_codigo": "CLIENT"},
]

CATEGORIAS_SEED = [
    # (nombre, descripción, nombre_del_padre, orden_display, es_primordial)
    ("Bebidas",             "Todas las bebidas",             None,             1, True),
    ("Bebidas Frías",       "Gaseosas, jugos, aguas",        "Bebidas",        1, False),
    ("Bebidas Calientes",   "Café, té, chocolate",           "Bebidas",        2, False),
    ("Sandwichs",           "Sandwichs fríos y calientes",   None,             2, False),
    ("Sandwichs Calientes", "Tostados, hamburguesas",        "Sandwichs",      1, False),
    ("Sandwichs Fríos",     "Sandwich de miga, ciabatta",    "Sandwichs",      2, False),
    ("Guarniciones",        "Papas fritas, aros de cebolla", None,             3, False),
    ("Postres",             "Flan, helado, tortas",          None,             4, False),
    ("Pizzas",              "Pizzas enteras y porciones",    None,             5, True),
    ("Tartas",              "Tartas dulces y saladas",       None,             6, True),
]

INGREDIENTES_SEED = [
    # (nombre, es_alergeno)
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

PRODUCTOS_SEED = [
    # (nombre, descripción, precio, tiempo_min, disponible,
    #   categorias=[(nombre_cat, es_principal)],
    #   ingredientes=[(nombre_ing, es_removible, es_principal, orden)])
    dict(
        nombre="Coca Cola 500ml",
        descripcion="Gaseosa sabor cola",
        precio=Decimal("1200.00"), tiempo=1, disponible=True,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[
            ("Agua", False, False, 1),
            ("Gasificación", False, False, 2),
            ("Azúcar", False, False, 3),
        ],
    ),
    dict(
        nombre="Café con Leche",
        descripcion="Café expreso con leche cremada",
        precio=Decimal("1500.00"), tiempo=5, disponible=True,
        categorias=[("Bebidas Calientes", True)],
        ingredientes=[("Café molido", False, True, 1), ("Leche", True, False, 2)],
    ),
    dict(
        nombre="Hamburguesa Clásica",
        descripcion="Medallón de res, cheddar, lechuga y tomate",
        precio=Decimal("4500.00"), tiempo=12, disponible=True,
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
        precio=Decimal("2800.00"), tiempo=5, disponible=True,
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
        precio=Decimal("2200.00"), tiempo=8, disponible=True,
        categorias=[("Guarniciones", True)],
        ingredientes=[
            ("Papa", False, True, 1),
            ("Aceite", False, False, 2),
            ("Sal", False, False, 3),
        ],
    ),
    dict(
        nombre="Flan con Dulce de Leche",
        descripcion="Flan casero con dulce de leche y crema",
        precio=Decimal("2500.00"), tiempo=2, disponible=True,
        categorias=[("Postres", True)],
        ingredientes=[
            ("Huevo", False, True, 1),
            ("Leche", False, False, 2),
            ("Dulce de leche", True, False, 3),
            ("Vainilla", False, False, 4),
        ],
    ),
    dict(
        nombre="Coca Cola",
        descripcion="Gaseosa sabor cola",
        precio=Decimal("0.00"), tiempo=1, disponible=True,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[
            ("Agua", False, False, 1),
            ("Gasificación", False, False, 2),
            ("Azúcar", False, False, 3),
        ],
        medidas=[
            ("250ml", Decimal("1500.00"), 10, 1),
            ("500ml", Decimal("2500.00"), 5, 2),
            ("1L", Decimal("4000.00"), 2, 3),
        ],
    ),
    dict(
        nombre="Pizza Muzzarella",
        descripcion="Pizza clásica con mozzarella y salsa",
        precio=Decimal("0.00"), tiempo=15, disponible=True,
        categorias=[("Pizzas", True)],
        ingredientes=[
            ("Harina de trigo", False, False, 1),
            ("Queso mozzarella", False, True, 2),
            ("Tomate", False, False, 3),
        ],
        medidas=[
            ("1 porción", Decimal("3000.00"), 20, 1),
            ("entera", Decimal("12000.00"), 5, 2),
        ],
    ),
    dict(
        nombre="Tarta de Jamón y Queso",
        descripcion="Tarta rellena de jamón cocido y queso",
        precio=Decimal("0.00"), tiempo=12, disponible=True,
        categorias=[("Tartas", True)],
        ingredientes=[
            ("Harina de trigo", False, True, 1),
            ("Huevo", False, False, 2),
            ("Queso mozzarella", False, False, 3),
        ],
        medidas=[
            ("1 porción", Decimal("2500.00"), 15, 1),
            ("media", Decimal("7000.00"), 8, 2),
            ("entera", Decimal("12000.00"), 3, 3),
        ],
    ),
]

ESTADOS_PEDIDO_SEED = [
    EstadoPedido(codigo="PENDIENTE",  descripcion="Pedido creado, pago pendiente",            orden=1, es_terminal=False),
    EstadoPedido(codigo="CONFIRMADO", descripcion="Pago procesado y confirmado",              orden=2, es_terminal=False),
    EstadoPedido(codigo="EN_PREP",    descripcion="En preparación en cocina",                  orden=3, es_terminal=False),
    EstadoPedido(codigo="EN_CAMINO",  descripcion="Despachado al cliente",                    orden=4, es_terminal=False),
    EstadoPedido(codigo="ENTREGADO",  descripcion="Entrega confirmada",                       orden=5, es_terminal=True),
    EstadoPedido(codigo="CANCELADO",  descripcion="Pedido cancelado",                         orden=6, es_terminal=True),
]

FORMAS_PAGO_SEED = [
    FormaPago(codigo="MERCADOPAGO",   descripcion="MercadoPago",      habilitado=True),
    FormaPago(codigo="EFECTIVO",      descripcion="Efectivo",         habilitado=True),
    FormaPago(codigo="TRANSFERENCIA", descripcion="Transferencia",    habilitado=True),
]


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_by_name(session: Session, model_cls, name: str):
    return session.exec(select(model_cls).where(model_cls.nombre == name)).first()


# ═══════════════════════════════════════════════════════════════
#  SEED FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def seed_roles(session: Session):
    for rol in ROLES_SEED:
        existing = session.exec(select(Rol).where(Rol.codigo == rol.codigo)).first()
        if not existing:
            session.add(rol)
    session.commit()


def seed_users(session: Session):
    for user_data in USERS_SEED:
        existing = session.exec(
            select(Usuario).where(Usuario.email == user_data["email"])
        ).first()
        if existing:
            continue

        nuevo = Usuario(
            nombre=user_data["nombre"],
            apellido=user_data["apellido"],
            email=user_data["email"],
            password_hash=get_password_hash(user_data["password"]),
        )
        session.add(nuevo)
        session.flush()

        enlace = UsuarioRol(
            usuario_id=nuevo.id,
            rol_codigo=user_data["rol_codigo"],
        )
        session.add(enlace)
    session.commit()


def seed_categorias(session: Session):
    """Crea categorías jerárquicas (dos pasadas: crear, luego asignar padres)."""
    created: dict[str, Categoria] = {}

    # Primera pasada: crear todas
    for nombre, desc, parent_nombre, orden, primordial in CATEGORIAS_SEED:
        existing = _get_by_name(session, Categoria, nombre)
        if existing:
            created[nombre] = existing
            continue
        cat = Categoria(nombre=nombre, descripcion=desc, orden_display=orden, es_primordial=primordial)
        session.add(cat)
        session.flush()
        created[nombre] = cat

    session.commit()

    # Segunda pasada: asignar padres
    for nombre, desc, parent_nombre, orden, primordial in CATEGORIAS_SEED:
        if parent_nombre:
            cat = created.get(nombre) or _get_by_name(session, Categoria, nombre)
            parent = created.get(parent_nombre) or _get_by_name(session, Categoria, parent_nombre)
            if cat and parent and cat.parent_id is None:
                cat.parent_id = parent.id
                session.add(cat)

    session.commit()


def seed_ingredientes(session: Session):
    for nombre, alergeno in INGREDIENTES_SEED:
        existing = _get_by_name(session, Ingrediente, nombre)
        if existing:
            continue

        ing = Ingrediente(nombre=nombre, es_alergeno=alergeno)
        session.add(ing)
    session.commit()


def seed_productos(session: Session):
    """Crea productos con relaciones a categorías e ingredientes."""
    for prod_data in PRODUCTOS_SEED:
        existing = _get_by_name(session, Producto, prod_data["nombre"])
        if existing:
            continue

        tiene_medidas = "medidas" in prod_data and prod_data["medidas"]

        if tiene_medidas:
            stock = 0
            disponible = any(m[2] > 0 for m in prod_data["medidas"])  # m[2] = stock
        else:
            stock = random.randint(0, 500)
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
            cat = _get_by_name(session, Categoria, cat_nombre)
            if cat:
                session.add(ProductoCategoria(
                    producto_id=producto.id,
                    categoria_id=cat.id,
                    es_principal=es_principal,
                ))

        # Asignar ingredientes
        for ing_nombre, removible, principal, orden in prod_data["ingredientes"]:
            ing = _get_by_name(session, Ingrediente, ing_nombre)
            if ing:
                session.add(ProductoIngrediente(
                    producto_id=producto.id,
                    ingrediente_id=ing.id,
                    es_removible=removible,
                    es_principal=principal,
                    orden=orden,
                ))

        # Crear medidas si el producto las tiene
        if tiene_medidas:
            for m_nombre, m_precio, m_stock, m_orden in prod_data["medidas"]:
                session.add(ProductoMedida(
                    producto_id=producto.id,
                    nombre=m_nombre,
                    precio=m_precio,
                    stock=m_stock,
                    orden=m_orden,
                ))

    session.commit()


def seed_estados_pedido(session: Session):
    for estado in ESTADOS_PEDIDO_SEED:
        existing = session.exec(
            select(EstadoPedido).where(EstadoPedido.codigo == estado.codigo)
        ).first()
        if not existing:
            session.add(estado)
    session.commit()


def seed_formas_pago(session: Session):
    for fp in FORMAS_PAGO_SEED:
        existing = session.exec(
            select(FormaPago).where(FormaPago.codigo == fp.codigo)
        ).first()
        if not existing:
            session.add(fp)
    session.commit()


# ═══════════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════════

def run_seed():
    """Run all seeds. Callable from lifespan."""
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


if __name__ == "__main__":
    run_seed()
    print("Seed completado.")
