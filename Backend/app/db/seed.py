"""
Database seeding module.

Populates the database with initial reference data required for the
application to function: roles, admin users, product categories,
ingredients, products, order states, and payment methods.

Runs automatically during application startup (via the lifespan hook
in main.py), and is also invocable directly as a standalone script.

Idempotent: all seed functions check for existing records before
inserting, so it is safe to run multiple times without creating
duplicates.
"""

import os
from decimal import Decimal
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session, select

# ── Roles & Auth ──
from modules.IdentidadYAcceso.Rol.models import Rol
from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from core.security import get_password_hash

# ── Addresses ──
from modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega

# ── Catalog ──
from modules.CatalogoDeProductos.Categoria.models import Categoria
from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from modules.CatalogoDeProductos.Producto.models import Producto
from modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
from modules.CatalogoDeProductos.Producto.service import ProductoService

# ── Sales ──
from modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
from modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


# ═══════════════════════════════════════════════════════════════
#  SEED DATA DEFINITIONS
# ═══════════════════════════════════════════════════════════════

# Four system roles covering the main access levels:
# ADMIN (full access), STOCK (inventory management),
# PEDIDOS (order management), CLIENT (self-service only)
ROLES_SEED = [
    Rol(codigo="ADMIN",   nombre="Administrador", descripcion="Acceso total sin restricciones"),
    Rol(codigo="STOCK",   nombre="Stock",         descripcion="Actualiza stock y disponibilidad"),
    Rol(codigo="PEDIDOS", nombre="Pedidos",       descripcion="Gestiona estados de pedido"),
    Rol(codigo="CLIENT",  nombre="Cliente",       descripcion="Opera solo con sus propios datos"),
]

# One user per role for initial testing and development
USERS_SEED = [
    {"nombre": "Admin",   "apellido": "Sistema",  "email": "admin@email.com",   "password": "admin123",   "rol_codigo": "ADMIN"},
    {"nombre": "Stock",   "apellido": "Sistema",  "email": "stock@email.com",   "password": "stock123",   "rol_codigo": "STOCK"},
    {"nombre": "Pedidos", "apellido": "Sistema",  "email": "pedidos@email.com", "password": "pedidos123", "rol_codigo": "PEDIDOS"},
    {"nombre": "Cliente", "apellido": "Estandar", "email": "client@email.com",  "password": "client123",  "rol_codigo": "CLIENT"},
]

# Default delivery addresses for each seed user
DIRECCIONES_SEED = [
    {"email": "admin@email.com",   "alias": "Principal", "linea1": "Av. Siempre Viva 123",      "ciudad": "Mendoza",   "es_principal": True},
    {"email": "stock@email.com",   "alias": "Principal", "linea1": "Calle falsa 456",            "ciudad": "Mendoza",   "es_principal": True},
    {"email": "pedidos@email.com", "alias": "Principal", "linea1": "Av. del Libertador 789",     "ciudad": "Godoy Cruz", "es_principal": True},
    {"email": "client@email.com",  "alias": "Principal", "linea1": "Av. Festa 1233",             "ciudad": "Mendoza",   "es_principal": True},
]

# Hierarchical product categories with display ordering.
# parent_none = top-level category, named parent links subcategories.
CATEGORIAS_SEED = [
    ("Bebidas",             "Todas las bebidas",             None,             1),
    ("Bebidas Frías",       "Gaseosas, jugos, aguas",        "Bebidas",        1),
    ("Bebidas Calientes",   "Café, té, chocolate",           "Bebidas",        2),
    ("Sandwichs",           "Sandwichs fríos y calientes",   None,             2),
    ("Sandwichs Calientes", "Tostados, hamburguesas",        "Sandwichs",      1),
    ("Sandwichs Fríos",     "Sandwich de miga, ciabatta",    "Sandwichs",      2),
    ("Guarniciones",        "Papas fritas, aros de cebolla", None,             3),
    ("Postres",             "Flan, helado, tortas",          None,             4),
    ("Pizzas",              "Pizzas enteras y porciones",    None,             5),
    ("Tartas",              "Tartas dulces y saladas",       None,             6),
]

# Ingredients with stock levels, prices, and allergen flags.
# es_alergeno=True means this ingredient is a common allergen.
INGREDIENTES_SEED = [
    ("Pan de Hamburguesa x und",     False, Decimal("50"),   500),
    ("Pan de Miga x und",           False, Decimal("60"),   300),
    ("Pan Ciabatta x und",          False, Decimal("80"),   200),
    ("Medallón de Carne Res x und", False, Decimal("200"),  200),
    ("Pechuga de Pollo x kg",       False, Decimal("1800"), 50),
    ("Queso Cheddar x kg",          True,  Decimal("800"),  30),
    ("Queso Mozzarella x kg",       True,  Decimal("900"),  25),
    ("Lechuga x und",               False, Decimal("30"),   150),
    ("Tomate x kg",                 False, Decimal("250"),  18),
    ("Cebolla x kg",                False, Decimal("200"),  20),
    ("Huevo x docena",              True,  Decimal("180"),  50),
    ("Mayonesa x 1 lt",             True,  Decimal("400"),  20),
    ("Mostaza x 1 lt",              False, Decimal("350"),  15),
    ("Ketchup x 1 lt",              False, Decimal("300"),  20),
    ("Papa x kg",                   False, Decimal("450"),  60),
    ("Aceite Girasol x 1 lt",       False, Decimal("600"),  20),
    ("Sal Fina x 1 kg",             False, Decimal("100"),  20),
    ("Café Molido x 1/2 kg",        False, Decimal("1500"), 10),
    ("Cartón de Leche Entera 1 lt", True,  Decimal("700"),  30),
    ("Crema de Leche x 1 lt",       True,  Decimal("900"),  15),
    ("Chocolate cobertura x kg",    True,  Decimal("1200"), 10),
    ("Paquete de Harina 0000 1 kg", True,  Decimal("400"),  40),
    ("Azúcar x kg",                 False, Decimal("350"),  30),
    ("Agua mineral x 1 lt",         False, Decimal("50"),   200),
    ("Gasificación x 1 lt",         False, Decimal("100"),  50),
    ("Levadura x 100 gr",           False, Decimal("250"),  20),
    ("Manteca x 200 gr",            True,  Decimal("800"),  15),
    ("Dulce de Leche x 1 kg",       True,  Decimal("1100"), 10),
    ("Esencia de Vainilla x 50 ml", False, Decimal("200"),  20),
    ("Hielo x bolsa 2 kg",          False, Decimal("50"),   100),
    ("Jamón Cocido x kg",           False, Decimal("1200"), 15),
]

# Products with their category assignments and ingredient compositions.
# Products with ingredients get their precio_base recalculated from
# ingredient costs via ProductoService._recalcular_precio_producto().
PRODUCTOS_SEED = [
    # ── Beverages (resold, no ingredient composition) ──
    dict(
        nombre="Coca Cola 500ml",
        descripcion="Gaseosa sabor cola 500ml",
        precio=Decimal("1200.00"), tiempo=1, disponible=True, stock_cantidad=200,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[],
    ),
    dict(
        nombre="Coca Cola 1L",
        descripcion="Gaseosa sabor cola 1 litro",
        precio=Decimal("1800.00"), tiempo=1, disponible=True, stock_cantidad=150,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[],
    ),
    dict(
        nombre="Coca Cola 2L",
        descripcion="Gaseosa sabor cola 2 litros",
        precio=Decimal("2500.00"), tiempo=1, disponible=True, stock_cantidad=100,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[],
    ),
    dict(
        nombre="Agua Mineral 500ml",
        descripcion="Agua mineral sin gas 500ml",
        precio=Decimal("600.00"), tiempo=1, disponible=True, stock_cantidad=300,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[],
    ),
    # ── Made-to-order products (with ingredient recipes) ──
    dict(
        nombre="Café con Leche",
        descripcion="Café expreso con leche cremada",
        precio=Decimal("1500.00"), tiempo=5, disponible=True, stock_cantidad=150,
        categorias=[("Bebidas Calientes", True)],
        ingredientes=[
            ("Café Molido x 1/2 kg", False, True, 1, 1),
            ("Cartón de Leche Entera 1 lt", True, False, 2, 1),
        ],
    ),
    dict(
        nombre="Hamburguesa Clásica",
        descripcion="Medallón de res, cheddar, lechuga y tomate",
        precio=Decimal("4500.00"), tiempo=12, disponible=True, stock_cantidad=100,
        categorias=[("Sandwichs Calientes", True)],
        ingredientes=[
            ("Pan de Hamburguesa x und", False, False, 1, 1),
            ("Medallón de Carne Res x und", False, True, 2, 1),
            ("Queso Cheddar x kg", True, False, 3, 1),
            ("Lechuga x und", True, False, 4, 1),
            ("Tomate x kg", True, False, 5, 1),
        ],
    ),
    dict(
        nombre="Sandwich de Miga (Jamón y Queso)",
        descripcion="Triple de jamón cocido, queso y mayonesa",
        precio=Decimal("2800.00"), tiempo=5, disponible=True, stock_cantidad=80,
        categorias=[("Sandwichs Fríos", True)],
        ingredientes=[
            ("Pan de Miga x und", False, False, 1, 2),
            ("Queso Mozzarella x kg", False, True, 2, 1),
            ("Mayonesa x 1 lt", True, False, 3, 1),
            ("Jamón Cocido x kg", False, False, 4, 1),
        ],
    ),
    dict(
        nombre="Papas Fritas Grandes",
        descripcion="Porción de papas fritas crocantes",
        precio=Decimal("2200.00"), tiempo=8, disponible=True, stock_cantidad=120,
        categorias=[("Guarniciones", True)],
        ingredientes=[
            ("Papa x kg", False, True, 1, 1),
            ("Aceite Girasol x 1 lt", False, False, 2, 1),
            ("Sal Fina x 1 kg", False, False, 3, 1),
        ],
    ),
    dict(
        nombre="Flan con Dulce de Leche",
        descripcion="Flan casero con dulce de leche y crema",
        precio=Decimal("2500.00"), tiempo=2, disponible=True, stock_cantidad=60,
        categorias=[("Postres", True)],
        ingredientes=[
            ("Huevo x docena", False, True, 1, 1),
            ("Cartón de Leche Entera 1 lt", False, False, 2, 1),
            ("Dulce de Leche x 1 kg", True, False, 3, 1),
            ("Esencia de Vainilla x 50 ml", False, False, 4, 1),
        ],
    ),
    dict(
        nombre="Pizza Muzzarella",
        descripcion="Pizza clásica con mozzarella y salsa",
        precio=Decimal("3000.00"), tiempo=15, disponible=True, stock_cantidad=90,
        categorias=[("Pizzas", True)],
        ingredientes=[
            ("Paquete de Harina 0000 1 kg", False, False, 1, 1),
            ("Queso Mozzarella x kg", False, True, 2, 1),
            ("Tomate x kg", False, False, 3, 1),
        ],
    ),
    dict(
        nombre="Tarta de Jamón y Queso",
        descripcion="Tarta rellena de jamón cocido y queso",
        precio=Decimal("2500.00"), tiempo=12, disponible=True, stock_cantidad=70,
        categorias=[("Tartas", True)],
        ingredientes=[
            ("Paquete de Harina 0000 1 kg", False, True, 1, 1),
            ("Huevo x docena", False, False, 2, 1),
            ("Queso Mozzarella x kg", False, False, 3, 1),
            ("Jamón Cocido x kg", False, False, 4, 1),
        ],
    ),
]

# Order lifecycle states arranged in a linear workflow.
# es_terminal=True means this state is an endpoint (no further transitions).
ESTADOS_PEDIDO_SEED = [
    EstadoPedido(codigo="PENDIENTE",  descripcion="Pedido creado, pago pendiente",            orden=1, es_terminal=False),
    EstadoPedido(codigo="CONFIRMADO", descripcion="Pago procesado y confirmado",              orden=2, es_terminal=False),
    EstadoPedido(codigo="EN_PREP",    descripcion="En preparación en cocina",                  orden=3, es_terminal=False),
    EstadoPedido(codigo="EN_CAMINO",  descripcion="Despachado al cliente",                    orden=4, es_terminal=False),
    EstadoPedido(codigo="ENTREGADO",  descripcion="Entrega confirmada",                       orden=5, es_terminal=True),
    EstadoPedido(codigo="CANCELADO",  descripcion="Pedido cancelado",                         orden=6, es_terminal=True),
]

# Supported payment methods for order processing
FORMAS_PAGO_SEED = [
    FormaPago(codigo="MERCADOPAGO",   descripcion="MercadoPago",      habilitado=True),
    FormaPago(codigo="EFECTIVO",      descripcion="Efectivo",         habilitado=True),
    FormaPago(codigo="TRANSFERENCIA", descripcion="Transferencia",    habilitado=True),
]


# ═══════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _get_by_name(session: Session, model_cls, name: str):
    """
    Retrieve a record by its 'nombre' field.

    Underscore prefix marks this as an internal implementation detail.
    Assumes the model class has a 'nombre' column.
    Returns the first match or None if not found.
    """
    return session.exec(select(model_cls).where(model_cls.nombre == name)).first()


# ═══════════════════════════════════════════════════════════════
#  SEED FUNCTIONS (one per entity type, all idempotent)
# ═══════════════════════════════════════════════════════════════

def seed_roles(session: Session):
    """
    Create predefined system roles idempotently.

    Skips roles that already exist in the database (matched by codigo PK).
    """
    for rol in ROLES_SEED:
        existing = session.exec(select(Rol).where(Rol.codigo == rol.codigo)).first()
        if not existing:
            session.add(rol)
    session.commit()


def seed_users(session: Session):
    """
    Create predefined user accounts idempotently.

    Each user is created with their role assignment via the UsuarioRol
    join table. Passwords are hashed with bcrypt before storage.
    Skips users whose email already exists in the database.
    """
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

        # Assign the corresponding role via the many-to-many join table
        enlace = UsuarioRol(
            usuario_id=nuevo.id,
            rol_codigo=user_data["rol_codigo"],
        )
        session.add(enlace)
    session.commit()


def seed_direcciones(session: Session):
    """
    Create default delivery addresses for each seed user.

    Idempotent: skips if an address with the same linea1 already exists
    for that user. Assumes seed users have already been created.
    """
    for dir_data in DIRECCIONES_SEED:
        usuario = session.exec(
            select(Usuario).where(Usuario.email == dir_data["email"])
        ).first()
        if not usuario:
            continue

        # Skip if this user already has this address
        existing = session.exec(
            select(DireccionEntrega).where(
                DireccionEntrega.usuario_id == usuario.id,
                DireccionEntrega.linea1 == dir_data["linea1"],
            )
        ).first()
        if existing:
            continue

        direccion = DireccionEntrega(
            usuario_id=usuario.id,
            alias=dir_data["alias"],
            linea1=dir_data["linea1"],
            ciudad=dir_data["ciudad"],
            es_principal=dir_data["es_principal"],
        )
        session.add(direccion)
    session.commit()


def seed_categorias(session: Session):
    """
    Create hierarchical product categories in two passes.

    First pass: create all categories (roots and children alike).
    Second pass: assign parent_id relationships for subcategories.
    This two-pass approach avoids FK constraint issues with circular
    dependencies during creation.
    """
    created: dict[str, Categoria] = {}

    # Pass 1: create all categories
    for nombre, desc, parent_nombre, orden in CATEGORIAS_SEED:
        existing = _get_by_name(session, Categoria, nombre)
        if existing:
            created[nombre] = existing
            continue
        cat = Categoria(nombre=nombre, descripcion=desc, orden_display=orden)
        session.add(cat)
        session.flush()
        created[nombre] = cat

    session.commit()

    # Pass 2: link subcategories to their parents
    for nombre, desc, parent_nombre, orden in CATEGORIAS_SEED:
        if parent_nombre:
            cat = created.get(nombre) or _get_by_name(session, Categoria, nombre)
            parent = created.get(parent_nombre) or _get_by_name(session, Categoria, parent_nombre)
            if cat and parent and cat.parent_id is None:
                cat.parent_id = parent.id
                session.add(cat)

    session.commit()


def seed_ingredientes(session: Session):
    """
    Create ingredients with stock and pricing information.

    Idempotent: skips ingredients that already exist (matched by name).
    Each ingredient tracks current stock, unit price, and allergen status.
    """
    for nombre, alergeno, precio, stock in INGREDIENTES_SEED:
        existing = _get_by_name(session, Ingrediente, nombre)
        if existing:
            continue

        ing = Ingrediente(
            nombre=nombre,
            es_alergeno=alergeno,
            precio_actual=precio,
            stock_actual=stock,
        )
        session.add(ing)
    session.commit()


def seed_productos(session: Session):
    """
    Create products with their category and ingredient relationships.

    For products with ingredients, the base price is recalculated from
    the sum of ingredient costs using ProductoService. Products without
    ingredients (resold items) use the price provided in the seed data.

    Idempotent: skips products that already exist (matched by name).
    """
    for prod_data in PRODUCTOS_SEED:
        existing = _get_by_name(session, Producto, prod_data["nombre"])
        if existing:
            continue

        stock_cantidad = prod_data["stock_cantidad"]
        # A product is only available if it has stock
        disponible = prod_data["disponible"] and stock_cantidad > 0

        producto = Producto(
            nombre=prod_data["nombre"],
            descripcion=prod_data["descripcion"],
            precio_base=prod_data["precio"],
            stock_cantidad=stock_cantidad,
            tiempo_prep_min=prod_data["tiempo"],
            disponible=disponible,
        )
        session.add(producto)
        session.flush()

        # Assign product to categories
        for cat_nombre, es_principal in prod_data["categorias"]:
            cat = _get_by_name(session, Categoria, cat_nombre)
            if cat:
                session.add(ProductoCategoria(
                    producto_id=producto.id,
                    categoria_id=cat.id,
                    es_principal=es_principal,
                ))

        # Assign ingredients to the product recipe
        for ing_nombre, removible, principal, orden, cantidad in prod_data["ingredientes"]:
            ing = _get_by_name(session, Ingrediente, ing_nombre)
            if ing:
                session.add(ProductoIngrediente(
                    producto_id=producto.id,
                    ingrediente_id=ing.id,
                    es_removible=removible,
                    es_principal=principal,
                    orden=orden,
                    cantidad=cantidad,
                ))

        # Recalculate base price from ingredient costs if applicable
        if prod_data["ingredientes"]:
            ProductoService._recalcular_precio_producto(session, producto.id)

    session.commit()


def seed_estados_pedido(session: Session):
    """
    Create order lifecycle states idempotently.

    Each state has a codigo PK, display name, sequential ordering,
    and a flag indicating whether it is a terminal (final) state.
    """
    for estado in ESTADOS_PEDIDO_SEED:
        existing = session.exec(
            select(EstadoPedido).where(EstadoPedido.codigo == estado.codigo)
        ).first()
        if not existing:
            session.add(estado)
    session.commit()


def seed_formas_pago(session: Session):
    """
    Create supported payment methods idempotently.

    Each payment method has a codigo PK, display description, and
    a habilitado (enabled) flag for soft toggle support.
    """
    for fp in FORMAS_PAGO_SEED:
        existing = session.exec(
            select(FormaPago).where(FormaPago.codigo == fp.codigo)
        ).first()
        if not existing:
            session.add(fp)
    session.commit()


# ═══════════════════════════════════════════════════════════════
#  MAIN SEED RUNNER
# ═══════════════════════════════════════════════════════════════

def run_seed():
    """
    Execute all seed functions in dependency order.

    Roles must be seeded first (FK dependency for users).
    Users before addresses (FK dependency for direcciones).
    Categories and ingredients before products (FK dependencies).
    Called automatically from the application lifespan hook.
    """
    engine = create_engine(DATABASE_URL, echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_roles(session)
        seed_users(session)
        seed_direcciones(session)
        seed_categorias(session)
        seed_ingredientes(session)
        seed_productos(session)
        seed_estados_pedido(session)
        seed_formas_pago(session)


# Allow running as a standalone script: `python -m app.db.seed`
if __name__ == "__main__":
    run_seed()
    print("Seed completado.")
