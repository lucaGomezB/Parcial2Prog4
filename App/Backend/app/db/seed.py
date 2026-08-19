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
from app.modules.IdentidadYAcceso.Rol.models import Rol
from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from app.modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from app.core.security import get_password_hash

# ── Addresses ──
from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega

# ── Catalog ──
from app.modules.CatalogoDeProductos.Categoria.models import Categoria
from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from app.modules.CatalogoDeProductos.Producto.models import Producto
from app.modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
from app.modules.CatalogoDeProductos.Producto.service import ProductoService
from app.modules.CatalogoDeProductos.UnidadMedida.models import UnidadMedida
from app.modules.CatalogoDeProductos.uow import CatalogoDeProductosUnitOfWork

# ── Sales ──
from app.modules.VentasPagosTrazabilidad.EstadoPedido.models import EstadoPedido
from app.modules.VentasPagosTrazabilidad.FormaPago.models import FormaPago
from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido

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

# Default delivery addresses for each seed user.
# Only admin has es_principal=True; the rest start as non-principal.
# Users can set their own principal address later via the UI.
DIRECCIONES_SEED = [
    {"email": "admin@email.com",   "alias": "Principal", "linea1": "Av. Siempre Viva 123",  "linea2": None, "ciudad": "Mendoza",   "provincia": "Mendoza", "codigo_postal": "5500", "es_principal": True},
    {"email": "stock@email.com",   "alias": "Principal", "linea1": "Calle falsa 456",        "linea2": None, "ciudad": "Mendoza",   "provincia": "Mendoza", "codigo_postal": "5500", "es_principal": False},
    {"email": "pedidos@email.com", "alias": "Principal", "linea1": "Av. del Libertador 789", "linea2": None, "ciudad": "Godoy Cruz", "provincia": "Mendoza", "codigo_postal": "5501", "es_principal": False},
    {"email": "client@email.com",  "alias": "Principal", "linea1": "Av. Festa 1233",         "linea2": None, "ciudad": "Mendoza",   "provincia": "Mendoza", "codigo_postal": "5500", "es_principal": False},
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
# Names are CLEAN — no unit suffixes. Unit/quantity data is now structured
# in ProductoIngrediente rows via unidad_medida_id and Decimal cantidad.
# Ingredients with stock, pricing, and measurement unit.
# Each tuple is (nombre, descripcion, es_alergeno, precio_actual, stock_actual, unidad_medida_id).
# unidad_medida_id: FK to unidadmedida — the unit in which stock_actual is tracked.
# IDs: 1=kg, 2=g, 3=L, 4=mL, 5=porcion, 6=docena, 7=m²
INGREDIENTES_SEED = [
    ("Pan de Hamburguesa",     "Pan suave para hamburguesas",                                      False, Decimal("50"),   500, 5),
    ("Pan de Miga",            "Pan de miga para sandwich",                                        False, Decimal("60"),   300, 5),
    ("Pan Ciabatta",           "Pan italiano tipo ciabatta",                                       False, Decimal("80"),   200, 5),
    ("Medallón de Carne Res",  "Medallón de carne vacuna",                                         False, Decimal("200"),  200, 5),
    ("Pechuga de Pollo",       "Pechuga de pollo fresca",                                          False, Decimal("1800"), 50,  1),
    ("Queso Cheddar",          "Queso cheddar",                                                    True,  Decimal("800"),  30,  1),
    ("Queso Mozzarella",       "Queso mozzarella",                                                 True,  Decimal("900"),  25,  1),
    ("Lechuga",                "Lechuga fresca",                                                   False, Decimal("30"),   150, 5),
    ("Tomate",                 "Tomate fresco",                                                    False, Decimal("250"),  18,  1),
    ("Cebolla",                "Cebolla fresca",                                                   False, Decimal("200"),  20,  1),
    ("Huevo",                  "Huevo fresco",                                                     True,  Decimal("180"),  50,  6),
    ("Mayonesa",               "Mayonesa",                                                         True,  Decimal("400"),  20,  3),
    ("Mostaza",                "Mostaza",                                                          False, Decimal("350"),  15,  3),
    ("Ketchup",                "Ketchup",                                                          False, Decimal("300"),  20,  3),
    ("Papa",                   "Papa fresca",                                                      False, Decimal("450"),  60,  1),
    ("Aceite Girasol",         "Aceite de girasol",                                                False, Decimal("600"),  20,  3),
    ("Sal Fina",               "Sal fina",                                                         False, Decimal("100"),  20,  1),
    ("Café Molido",            "Café molido",                                                      False, Decimal("1500"), 10,  1),
    ("Leche Entera",           "Leche entera pasteurizada",                                        True,  Decimal("700"),  30,  3),
    ("Crema de Leche",         "Crema de leche",                                                   True,  Decimal("900"),  15,  3),
    ("Chocolate Cobertura",    "Chocolate para cobertura",                                         True,  Decimal("1200"), 10,  1),
    ("Harina 0000",            "Harina 0000",                                                      True,  Decimal("400"),  40,  1),
    ("Azúcar",                 "Azúcar refinada",                                                  False, Decimal("350"),  30,  1),
    ("Agua Mineral",           "Agua mineral sin gas",                                             False, Decimal("50"),   200, 3),
    ("Gasificación",           "Agua gasificada",                                                  False, Decimal("100"),  50,  3),
    ("Levadura",               "Levadura fresca",                                                  False, Decimal("250"),  20,  2),
    ("Manteca",                "Manteca",                                                          True,  Decimal("800"),  15,  2),
    ("Dulce de Leche",         "Dulce de leche",                                                   True,  Decimal("1100"), 10,  1),
    ("Esencia de Vainilla",    "Esencia de vainilla",                                              False, Decimal("200"),  50,  4),
    ("Hielo",                  "Hielo en bolsa",                                                   False, Decimal("50"),   100, 1),
    ("Jamón Cocido",           "Jamón cocido",                                                     False, Decimal("1200"), 15,  1),
]

# Mapping old suffixed ingredient names to new clean names.
# Used by the seeder for idempotent rename (task 7.9).
_INGREDIENT_NAME_RENAME = {
    "Pan de Hamburguesa x und":     "Pan de Hamburguesa",
    "Pan de Miga x und":           "Pan de Miga",
    "Pan Ciabatta x und":          "Pan Ciabatta",
    "Medallón de Carne Res x und": "Medallón de Carne Res",
    "Pechuga de Pollo x kg":       "Pechuga de Pollo",
    "Queso Cheddar x kg":          "Queso Cheddar",
    "Queso Mozzarella x kg":       "Queso Mozzarella",
    "Lechuga x und":               "Lechuga",
    "Tomate x kg":                 "Tomate",
    "Cebolla x kg":                "Cebolla",
    "Huevo x docena":              "Huevo",
    "Mayonesa x 1 lt":             "Mayonesa",
    "Mostaza x 1 lt":              "Mostaza",
    "Ketchup x 1 lt":              "Ketchup",
    "Papa x kg":                   "Papa",
    "Aceite Girasol x 1 lt":       "Aceite Girasol",
    "Sal Fina x 1 kg":             "Sal Fina",
    "Café Molido x 1/2 kg":        "Café Molido",
    "Cartón de Leche Entera 1 lt": "Leche Entera",
    "Crema de Leche x 1 lt":       "Crema de Leche",
    "Chocolate cobertura x kg":    "Chocolate Cobertura",
    "Paquete de Harina 0000 1 kg": "Harina 0000",
    "Azúcar x kg":                 "Azúcar",
    "Agua mineral x 1 lt":         "Agua Mineral",
    "Gasificación x 1 lt":         "Gasificación",
    "Levadura x 100 gr":           "Levadura",
    "Manteca x 200 gr":            "Manteca",
    "Dulce de Leche x 1 kg":       "Dulce de Leche",
    "Esencia de Vainilla x 50 ml": "Esencia de Vainilla",
    "Hielo x bolsa 2 kg":          "Hielo",
    "Jamón Cocido x kg":           "Jamón Cocido",
}

# Products with their category assignments and ingredient compositions.
# Products with ingredients get their precio_base recalculated from
# ingredient costs via ProductoService._recalcular_precio_producto().
PRODUCTOS_SEED = [
    # ── Beverages (resold, no ingredient composition) ──
    # These are es_producto_terminado=True with stock_manual set.
    # No stock_cantidad param — stock comes from stock_manual via the API.
    dict(
        nombre="Coca Cola 500ml",
        descripcion="Gaseosa sabor cola 500ml",
        precio=Decimal("1200.00"), precio_actual=Decimal("1200.00"), tiempo=1, disponible=True,
        receta=None, imagenes_url=[], es_producto_terminado=True,
        stock_manual=200,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[],
    ),
    dict(
        nombre="Coca Cola 1L",
        descripcion="Gaseosa sabor cola 1 litro",
        precio=Decimal("1800.00"), precio_actual=Decimal("1800.00"), tiempo=1, disponible=True,
        receta=None, imagenes_url=[], es_producto_terminado=True,
        stock_manual=150,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[],
    ),
    dict(
        nombre="Coca Cola 2L",
        descripcion="Gaseosa sabor cola 2 litros",
        precio=Decimal("2500.00"), precio_actual=Decimal("2500.00"), tiempo=1, disponible=True,
        receta=None, imagenes_url=[], es_producto_terminado=True,
        stock_manual=100,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[],
    ),
    dict(
        nombre="Agua Mineral 500ml",
        descripcion="Agua mineral sin gas 500ml",
        precio=Decimal("600.00"), precio_actual=Decimal("600.00"), tiempo=1, disponible=True,
        receta=None, imagenes_url=[], es_producto_terminado=True,
        stock_manual=300,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[],
    ),
    # ── Made-to-order products (with ingredient recipes) ──
    # Ingredient tuples are 6-element: (ing_nombre, removible, principal, orden, cantidad, unidad_medida_id)
    # cantidad uses Decimal; unidad_medida_id: 1=kg, 2=g, 3=L, 4=mL, 5=porcion, 6=docena
    # No stock_cantidad param — derived stock is computed from ingredient availability.
    dict(
        nombre="Café con Leche",
        descripcion="Café expreso con leche cremada",
        precio=Decimal("1500.00"), precio_actual=Decimal("1500.00"), tiempo=5, disponible=True,
        receta="Café expreso combinado con leche entera cremada", imagenes_url=[], es_producto_terminado=False,
        categorias=[("Bebidas Calientes", True)],
        ingredientes=[
            ("Café Molido", False, True, 1, Decimal("0.500"), 1),
            ("Leche Entera", True, False, 2, Decimal("1"), 3),
        ],
    ),
    dict(
        nombre="Hamburguesa Clásica",
        descripcion="Medallón de res, cheddar, lechuga y tomate",
        precio=Decimal("4500.00"), precio_actual=Decimal("4500.00"), tiempo=12, disponible=True,
        receta="Medallón de res a la parrilla con queso cheddar, lechuga fresca y tomate en pan de hamburguesa", imagenes_url=[], es_producto_terminado=False,
        categorias=[("Sandwichs Calientes", True)],
        ingredientes=[
            ("Pan de Hamburguesa", False, False, 1, Decimal("1"), 5),
            ("Medallón de Carne Res", False, True, 2, Decimal("1"), 5),
            ("Queso Cheddar", True, False, 3, Decimal("1"), 1),
            ("Lechuga", True, False, 4, Decimal("1"), 5),
            ("Tomate", True, False, 5, Decimal("1"), 1),
        ],
    ),
    dict(
        nombre="Sandwich de Miga (Jamón y Queso)",
        descripcion="Triple de jamón cocido, queso y mayonesa",
        precio=Decimal("2800.00"), precio_actual=Decimal("2800.00"), tiempo=5, disponible=True,
        receta="Capas de pan de miga con jamón cocido, queso mozzarella y mayonesa", imagenes_url=[], es_producto_terminado=False,
        categorias=[("Sandwichs Fríos", True)],
        ingredientes=[
            ("Pan de Miga", False, False, 1, Decimal("2"), 5),
            ("Queso Mozzarella", False, True, 2, Decimal("1"), 1),
            ("Mayonesa", True, False, 3, Decimal("1"), 3),
            ("Jamón Cocido", False, False, 4, Decimal("1"), 1),
        ],
    ),
    dict(
        nombre="Papas Fritas Grandes",
        descripcion="Porción de papas fritas crocantes",
        precio=Decimal("2200.00"), precio_actual=Decimal("2200.00"), tiempo=8, disponible=True,
        receta="Papas cortadas en bastón fritas en aceite de girasol y sazonadas con sal", imagenes_url=[], es_producto_terminado=False,
        categorias=[("Guarniciones", True)],
        unidad_medida_id=5,
        ingredientes=[
            ("Papa", False, True, 1, Decimal("1"), 1),
            ("Aceite Girasol", False, False, 2, Decimal("1"), 3),
            ("Sal Fina", False, False, 3, Decimal("1"), 1),
        ],
    ),
    dict(
        nombre="Flan con Dulce de Leche",
        descripcion="Flan casero con dulce de leche y crema",
        precio=Decimal("2500.00"), precio_actual=Decimal("2500.00"), tiempo=2, disponible=True,
        receta="Flan casero a base de huevo, leche y esencia de vainilla, servido con dulce de leche y crema", imagenes_url=[], es_producto_terminado=False,
        categorias=[("Postres", True)],
        ingredientes=[
            ("Huevo", False, True, 1, Decimal("1"), 6),
            ("Leche Entera", False, False, 2, Decimal("1"), 3),
            ("Dulce de Leche", True, False, 3, Decimal("1"), 1),
            ("Esencia de Vainilla", False, False, 4, Decimal("50"), 4),
        ],
    ),
    dict(
        nombre="Pizza Muzzarella",
        descripcion="Pizza clásica con mozzarella y salsa",
        precio=Decimal("3000.00"), precio_actual=Decimal("3000.00"), tiempo=15, disponible=True,
        receta="Masa de pizza con salsa de tomate y queso mozzarella, horneada", imagenes_url=[], es_producto_terminado=False,
        categorias=[("Pizzas", True)],
        unidad_medida_id=5,
        ingredientes=[
            ("Harina 0000", False, False, 1, Decimal("1"), 1),
            ("Queso Mozzarella", False, True, 2, Decimal("1"), 1),
            ("Tomate", False, False, 3, Decimal("1"), 1),
        ],
    ),
    dict(
        nombre="Tarta de Jamón y Queso",
        descripcion="Tarta rellena de jamón cocido y queso",
        precio=Decimal("2500.00"), precio_actual=Decimal("2500.00"), tiempo=12, disponible=True,
        receta="Masa de tarta rellena de jamón cocido, queso mozzarella y huevo", imagenes_url=[], es_producto_terminado=False,
        categorias=[("Tartas", True)],
        ingredientes=[
            ("Harina 0000", False, True, 1, Decimal("1"), 1),
            ("Huevo", False, False, 2, Decimal("1"), 6),
            ("Queso Mozzarella", False, False, 3, Decimal("1"), 1),
            ("Jamón Cocido", False, False, 4, Decimal("1"), 1),
        ],
    ),
]

# Order lifecycle states arranged in a linear workflow.
# es_terminal=True means this state is an endpoint (no further transitions).
ESTADOS_PEDIDO_SEED = [
    EstadoPedido(codigo="PENDIENTE",  descripcion="Pedido creado, pago pendiente",  orden=1, es_terminal=False),
    EstadoPedido(codigo="CONFIRMADO", descripcion="Pago procesado y confirmado",    orden=2, es_terminal=False),
    EstadoPedido(codigo="EN_PREP",    descripcion="En preparacion en cocina",        orden=3, es_terminal=False),
    EstadoPedido(codigo="ENTREGADO",  descripcion="Entrega confirmada",             orden=4, es_terminal=True),
    EstadoPedido(codigo="CANCELADO",  descripcion="Pedido cancelado",               orden=5, es_terminal=True),
]

# Supported payment methods for order processing
FORMAS_PAGO_SEED = [
    FormaPago(codigo="MERCADOPAGO",   descripcion="MercadoPago",          habilitado=True),
    FormaPago(codigo="EFECTIVO",      descripcion="Efectivo",             habilitado=False),
    FormaPago(codigo="PAGO_LOCAL",    descripcion="Pago y retiro en local", habilitado=True),
    FormaPago(codigo="TRANSFERENCIA", descripcion="Transferencia",        habilitado=False),
]

# Standard measurement units for the product catalog.
# Each tuple is (nombre, simbolo, tipo, factor_conversion).
# factor_conversion: how many base units equal one of this unit.
# Base units (factor=1): gramo, mililitro, porcion, metro cuadrado.
UNIDADES_MEDIDA_SEED = [
    ("kilogramo", "kg", "masa", Decimal("1000")),
    ("gramo", "g", "masa", Decimal("1")),
    ("litro", "L", "volumen", Decimal("1000")),
    ("mililitro", "mL", "volumen", Decimal("1")),
    ("porcion", "unidad", "unidad", Decimal("1")),
    ("docena", "docena", "unidad", Decimal("12")),
    ("metro cuadrado", "m²", "area", Decimal("1")),
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
            linea2=dir_data.get("linea2"),
            ciudad=dir_data["ciudad"],
            provincia=dir_data.get("provincia"),
            codigo_postal=dir_data.get("codigo_postal"),
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

    Idempotent: first renames any existing ingredients from old suffixed names
    to clean names (task 7.9), then creates ingredients that don't yet exist.
    """
    # Step 1: Rename old-named ingredients to clean names (idempotent)
    for old_name, new_name in _INGREDIENT_NAME_RENAME.items():
        existing = _get_by_name(session, Ingrediente, old_name)
        if existing:
            # Check if the clean name already exists (conflict)
            conflict = _get_by_name(session, Ingrediente, new_name)
            if conflict and conflict.id != existing.id:
                # Another ingredient already has the clean name — skip rename
                # (this is unlikely in practice; old-named and clean-named
                #  ingredients shouldn't coexist unless manually inserted)
                continue
            existing.nombre = new_name
            session.add(existing)

    session.commit()

    # Step 2: Create any ingredients that don't exist yet (matched by clean name)
    for nombre, descripcion, alergeno, precio, stock, unidad_id in INGREDIENTES_SEED:
        existing = _get_by_name(session, Ingrediente, nombre)
        if existing:
            continue

        ing = Ingrediente(
            nombre=nombre,
            descripcion=descripcion,
            es_alergeno=alergeno,
            precio_actual=precio,
            stock_actual=stock,
            unidad_medida_id=unidad_id,
        )
        session.add(ing)
    session.commit()


def seed_productos(session: Session):
    """
    Create products with their category and ingredient relationships.

    For products with ingredients (es_producto_terminado=False), stock
    is derived from ingredient availability — no stock_cantidad is set.
    For finished/resale products (es_producto_terminado=True), stock_manual
    is set and stock_cantidad is left at default (0, ignored by API).

    Base price is recalculated from ingredient costs for products with
    ingredients. Products without ingredients use the price from seed data.

    Idempotent: skips products that already exist (matched by name).
    """
    for prod_data in PRODUCTOS_SEED:
        existing = _get_by_name(session, Producto, prod_data["nombre"])
        if existing:
            continue

        es_terminado = prod_data.get("es_producto_terminado", False)
        stock_manual = prod_data.get("stock_manual")

        # For es_producto_terminado=True products, available only if stock_manual > 0
        # For made-to-order products, always True (derived from ingredients)
        if es_terminado:
            disponible = prod_data["disponible"] and (stock_manual or 0) > 0
        else:
            disponible = prod_data["disponible"]

        producto = Producto(
            nombre=prod_data["nombre"],
            descripcion=prod_data["descripcion"],
            receta=prod_data.get("receta"),
            precio_base=prod_data["precio"],
            precio_actual=prod_data.get("precio_actual", prod_data["precio"]),
            imagenes_url=prod_data.get("imagenes_url", []),
            tiempo_prep_min=prod_data["tiempo"],
            disponible=disponible,
            es_producto_terminado=es_terminado,
            stock_manual=stock_manual,
            unidad_medida_id=prod_data.get("unidad_medida_id"),
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
        # 6-element tuple: (ing_nombre, removible, principal, orden, cantidad, unidad_medida_id)
        for ing_tuple in prod_data["ingredientes"]:
            ing_nombre, removible, principal, orden, cantidad = ing_tuple[:5]
            unidad_medida_id = ing_tuple[5] if len(ing_tuple) >= 6 else None
            ing = _get_by_name(session, Ingrediente, ing_nombre)
            if ing:
                session.add(ProductoIngrediente(
                    producto_id=producto.id,
                    ingrediente_id=ing.id,
                    es_removible=removible,
                    es_principal=principal,
                    orden=orden,
                    cantidad=cantidad,
                    unidad_medida_id=unidad_medida_id,
                ))

        # Recalculate base price and sync derived stock.
        # Must wrap in UoW — _recalcular_precio_producto expects a
        # CatalogoDeProductosUnitOfWork, not a raw Session.
        # Called for all products: ingredient-based (recalc price + stock)
        # and terminado (sync stock_manual → stock_cantidad).
        if prod_data["ingredientes"] or es_terminado:
            with CatalogoDeProductosUnitOfWork(session) as uow:
                ProductoService._recalcular_precio_producto(uow, producto.id)

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


def seed_unidades_medida(session: Session):
    """
    Create standard measurement units idempotently.

    Checks by simbolo (the UNIQUE business key) to avoid duplicates.
    If a unit with the same simbolo already exists but with a different
    nombre (e.g. 'pieza' renamed to 'porcion'), the existing row is
    updated in-place to preserve FK references from ingredientes and
    productos.

    When a base unit (factor_conversion=1) is not found by its simbolo,
    the function also checks whether another base unit already exists
    for the same tipo.  If the seed data changed the simbolo of a base
    unit (e.g. 'porcion' renamed to 'unidad'), the existing row is
    updated in-place rather than attempting a duplicate insert, which
    would violate the uq_unidad_base_por_tipo partial unique index.

    The 7 predefined units cover masa, volumen, unidad, and area types.
    Each unit carries its factor_conversion relative to its tipo's base unit.
    """
    for nombre, simbolo, tipo, factor in UNIDADES_MEDIDA_SEED:
        existing = session.exec(
            select(UnidadMedida).where(UnidadMedida.simbolo == simbolo)
        ).first()
        if existing:
            # Update fields if they differ (handles renames like pieza→porcion)
            updated = False
            if existing.nombre != nombre:
                existing.nombre = nombre
                updated = True
            if existing.tipo != tipo:
                existing.tipo = tipo
                updated = True
            if existing.factor_conversion != factor:
                existing.factor_conversion = factor
                updated = True
            if updated:
                session.add(existing)
        elif factor == Decimal("1"):
            # Base unit not found by new simbolo — check if another base
            # unit already exists for the same tipo (simbolo was renamed).
            existing_base = session.exec(
                select(UnidadMedida).where(
                    UnidadMedida.tipo == tipo,
                    UnidadMedida.factor_conversion == Decimal("1"),
                )
            ).first()
            if existing_base:
                existing_base.nombre = nombre
                existing_base.simbolo = simbolo
                session.add(existing_base)
            else:
                session.add(
                    UnidadMedida(
                        nombre=nombre,
                        simbolo=simbolo,
                        tipo=tipo,
                        factor_conversion=factor,
                    )
                )
        else:
            session.add(
                UnidadMedida(
                    nombre=nombre,
                    simbolo=simbolo,
                    tipo=tipo,
                    factor_conversion=factor,
                )
            )
    session.commit()


# ═══════════════════════════════════════════════════════════════
#  MAIN SEED RUNNER
# ═══════════════════════════════════════════════════════════════

def run_seed(fresh: bool = False):
    """
    Execute all seed functions in dependency order.

    Roles must be seeded first (FK dependency for users).
    Users before addresses (FK dependency for direcciones).
    Categories and ingredients before products (FK dependencies).
    Called automatically from the application lifespan hook.

    Args:
        fresh: If True, create all tables from SQLModel metadata first and
               stamp alembic head (for brand-new databases). If False,
               only run seed functions idempotently (for existing DBs).
    """
    engine = create_engine(DATABASE_URL, echo=False)

    if fresh:
        SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        seed_roles(session)
        seed_users(session)
        seed_direcciones(session)
        seed_categorias(session)
        seed_unidades_medida(session)
        seed_ingredientes(session)
        seed_productos(session)
        seed_estados_pedido(session)
        seed_formas_pago(session)

    # Only stamp head on fresh databases — on existing DBs alembic
    # manages the version table via command.upgrade in the lifespan.
    if fresh:
        try:
            from alembic.config import Config
            from alembic import command
            alembic_cfg = Config("alembic.ini")
            command.stamp(alembic_cfg, "head")
        except Exception:
            pass  # Non-fatal: seed data is already in place


# Allow running as a standalone script: `python -m app.db.seed`
if __name__ == "__main__":
    run_seed()
    print("Seed completado.")
