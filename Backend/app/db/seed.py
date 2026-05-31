"""
seed.py — Seed de datos para el backend.
Corre en el startup (lifespan de main.py) y también es invocable como script.

Idempotente: si un registro ya existe, lo saltea.
"""
import os
from decimal import Decimal
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session, select

# ── Roles & Auth ──
from modules.IdentidadYAcceso.Rol.models import Rol
from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from modules.IdentidadYAcceso.Usuario.service import get_password_hash

# ── Direcciones ──
from modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega

# ── Catálogo ──
from modules.CatalogoDeProductos.Categoria.models import Categoria
from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
from modules.CatalogoDeProductos.Producto.models import Producto
from modules.CatalogoDeProductos.producto_categoria import ProductoCategoria
from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
from modules.CatalogoDeProductos.Producto.service import ProductoService

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

DIRECCIONES_SEED = [
    {"email": "admin@email.com",   "alias": "Principal", "linea1": "Av. Siempre Viva 123",      "ciudad": "Mendoza",   "es_principal": True},
    {"email": "stock@email.com",   "alias": "Principal", "linea1": "Calle falsa 456",            "ciudad": "Mendoza",   "es_principal": True},
    {"email": "pedidos@email.com", "alias": "Principal", "linea1": "Av. del Libertador 789",     "ciudad": "Godoy Cruz", "es_principal": True},
    {"email": "client@email.com",  "alias": "Principal", "linea1": "Av. Festa 1233",             "ciudad": "Mendoza",   "es_principal": True},
]

CATEGORIAS_SEED = [
    # (nombre, descripción, nombre_del_padre, orden_display)
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

INGREDIENTES_SEED = [
    # (nombre, es_alergeno, precio_actual, stock_actual)
    ("Pan de hamburguesa",  False, Decimal("50"),   500),
    ("Pan de miga",         False, Decimal("60"),   300),
    ("Pan ciabatta",        False, Decimal("80"),   200),
    ("Carne de res",        False, Decimal("200"),  200),
    ("Pechuga de pollo",    False, Decimal("180"),  250),
    ("Queso cheddar",       True,  Decimal("80"),   300),
    ("Queso mozzarella",    True,  Decimal("90"),   250),
    ("Lechuga",             False, Decimal("30"),   150),
    ("Tomate",              False, Decimal("25"),   180),
    ("Cebolla",             False, Decimal("20"),   200),
    ("Huevo",               True,  Decimal("15"),   500),
    ("Mayonesa",            True,  Decimal("40"),   200),
    ("Mostaza",             False, Decimal("35"),   150),
    ("Ketchup",             False, Decimal("30"),   200),
    ("Papa",                False, Decimal("45"),   300),
    ("Aceite",              False, Decimal("60"),   200),
    ("Sal",                 False, Decimal("10"),   500),
    ("Café molido",         False, Decimal("150"),  100),
    ("Leche",               True,  Decimal("70"),   200),
    ("Crema de leche",      True,  Decimal("90"),   150),
    ("Chocolate",           True,  Decimal("120"),  100),
    ("Harina de trigo",     True,  Decimal("40"),   400),
    ("Azúcar",              False, Decimal("35"),   300),
    ("Hielo",               False, Decimal("5"),    1000),
    ("Gasificación",        False, Decimal("10"),   500),
    ("Agua",                False, Decimal("5"),    1000),
    ("Levadura",            False, Decimal("25"),   200),
    ("Manteca",             True,  Decimal("80"),   150),
    ("Dulce de leche",      True,  Decimal("110"),  100),
    ("Vainilla",            False, Decimal("200"),  50),
]

PRODUCTOS_SEED = [
    # (nombre, descripción, precio, tiempo_min, disponible,
    #   categorias=[(nombre_cat, es_principal)],
    #   ingredientes=[(nombre_ing, es_removible, es_principal, orden, cantidad)])
    dict(
        nombre="Coca Cola 500ml",
        descripcion="Gaseosa sabor cola",
        precio=Decimal("1200.00"), tiempo=1, disponible=True, stock_cantidad=200,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[
            ("Agua", False, False, 1, Decimal("0.5")),
            ("Gasificación", False, False, 2, Decimal("0.1")),
            ("Azúcar", False, False, 3, Decimal("0.2")),
        ],
    ),
    dict(
        nombre="Café con Leche",
        descripcion="Café expreso con leche cremada",
        precio=Decimal("1500.00"), tiempo=5, disponible=True, stock_cantidad=150,
        categorias=[("Bebidas Calientes", True)],
        ingredientes=[
            ("Café molido", False, True, 1, Decimal("0.05")),
            ("Leche", True, False, 2, Decimal("0.2")),
        ],
    ),
    dict(
        nombre="Hamburguesa Clásica",
        descripcion="Medallón de res, cheddar, lechuga y tomate",
        precio=Decimal("4500.00"), tiempo=12, disponible=True, stock_cantidad=100,
        categorias=[("Sandwichs Calientes", True)],
        ingredientes=[
            ("Pan de hamburguesa", False, False, 1, Decimal("1")),
            ("Carne de res", False, True, 2, Decimal("1")),
            ("Queso cheddar", True, False, 3, Decimal("2")),
            ("Lechuga", True, False, 4, Decimal("0.5")),
            ("Tomate", True, False, 5, Decimal("0.5")),
        ],
    ),
    dict(
        nombre="Sandwich de Miga (Jamón y Queso)",
        descripcion="Triple de jamón cocido, queso y mayonesa",
        precio=Decimal("2800.00"), tiempo=5, disponible=True, stock_cantidad=80,
        categorias=[("Sandwichs Fríos", True)],
        ingredientes=[
            ("Pan de miga", False, False, 1, Decimal("2")),
            ("Queso mozzarella", False, True, 2, Decimal("0.15")),
            ("Mayonesa", True, False, 3, Decimal("0.05")),
        ],
    ),
    dict(
        nombre="Papas Fritas Grandes",
        descripcion="Porción de papas fritas crocantes",
        precio=Decimal("2200.00"), tiempo=8, disponible=True, stock_cantidad=120,
        categorias=[("Guarniciones", True)],
        ingredientes=[
            ("Papa", False, True, 1, Decimal("0.5")),
            ("Aceite", False, False, 2, Decimal("0.1")),
            ("Sal", False, False, 3, Decimal("0.02")),
        ],
    ),
    dict(
        nombre="Flan con Dulce de Leche",
        descripcion="Flan casero con dulce de leche y crema",
        precio=Decimal("2500.00"), tiempo=2, disponible=True, stock_cantidad=60,
        categorias=[("Postres", True)],
        ingredientes=[
            ("Huevo", False, True, 1, Decimal("2")),
            ("Leche", False, False, 2, Decimal("0.25")),
            ("Dulce de leche", True, False, 3, Decimal("0.1")),
            ("Vainilla", False, False, 4, Decimal("0.02")),
        ],
    ),
    dict(
        nombre="Coca Cola",
        descripcion="Gaseosa sabor cola",
        precio=Decimal("1200.00"), tiempo=1, disponible=True, stock_cantidad=200,
        categorias=[("Bebidas Frías", True)],
        ingredientes=[
            ("Agua", False, False, 1, Decimal("0.5")),
            ("Gasificación", False, False, 2, Decimal("0.1")),
            ("Azúcar", False, False, 3, Decimal("0.2")),
        ],
    ),
    dict(
        nombre="Pizza Muzzarella",
        descripcion="Pizza clásica con mozzarella y salsa",
        precio=Decimal("3000.00"), tiempo=15, disponible=True, stock_cantidad=90,
        categorias=[("Pizzas", True)],
        ingredientes=[
            ("Harina de trigo", False, False, 1, Decimal("0.3")),
            ("Queso mozzarella", False, True, 2, Decimal("0.2")),
            ("Tomate", False, False, 3, Decimal("0.15")),
        ],
    ),
    dict(
        nombre="Tarta de Jamón y Queso",
        descripcion="Tarta rellena de jamón cocido y queso",
        precio=Decimal("2500.00"), tiempo=12, disponible=True, stock_cantidad=70,
        categorias=[("Tartas", True)],
        ingredientes=[
            ("Harina de trigo", False, True, 1, Decimal("0.3")),
            ("Huevo", False, False, 2, Decimal("2")),
            ("Queso mozzarella", False, False, 3, Decimal("0.15")),
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


def seed_direcciones(session: Session):
    """Crea direcciones de entrega para cada usuario.
    Idempotente: si ya existe una dirección con la misma línea para el usuario, la saltea.
    """
    for dir_data in DIRECCIONES_SEED:
        usuario = session.exec(
            select(Usuario).where(Usuario.email == dir_data["email"])
        ).first()
        if not usuario:
            continue

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
    """Crea categorías jerárquicas (dos pasadas: crear, luego asignar padres)."""
    created: dict[str, Categoria] = {}

    # Primera pasada: crear todas
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

    # Segunda pasada: asignar padres
    for nombre, desc, parent_nombre, orden in CATEGORIAS_SEED:
        if parent_nombre:
            cat = created.get(nombre) or _get_by_name(session, Categoria, nombre)
            parent = created.get(parent_nombre) or _get_by_name(session, Categoria, parent_nombre)
            if cat and parent and cat.parent_id is None:
                cat.parent_id = parent.id
                session.add(cat)

    session.commit()


def seed_ingredientes(session: Session):
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
    """Crea productos con relaciones a categorías e ingredientes.
    Idempotente: si el producto ya existe, lo saltea.
    Luego recalcula precio_base desde los ingredientes usando ProductoService.
    """
    for prod_data in PRODUCTOS_SEED:
        existing = _get_by_name(session, Producto, prod_data["nombre"])
        if existing:
            continue

        stock_cantidad = prod_data["stock_cantidad"]
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

        # Recalcular precio_base desde los ingredientes
        ProductoService._recalcular_precio_producto(session, producto.id)

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
        seed_direcciones(session)
        seed_categorias(session)
        seed_ingredientes(session)
        seed_productos(session)
        seed_estados_pedido(session)
        seed_formas_pago(session)


if __name__ == "__main__":
    run_seed()
    print("Seed completado.")
