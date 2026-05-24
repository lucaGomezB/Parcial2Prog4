import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session, select
from modules.IdentidadYAcceso.Rol.models import Rol
from modules.IdentidadYAcceso.Usuario.models import Usuario
from modules.IdentidadYAcceso.usuario_rol import UsuarioRol
from modules.IdentidadYAcceso.Usuario.service import get_password_hash

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

ROLES_SEED = [
    Rol(codigo="ADMIN", nombre="Administrador", descripcion="Acceso total sin restricciones"),
    Rol(codigo="STOCK", nombre="Stock", descripcion="Actualiza el stock y disponibilidad de productos"),
    Rol(codigo="PEDIDOS", nombre="Pedidos", descripcion="Avanza estados de pedido de CONFIRMADO a ENTREGADO"),
    Rol(codigo="CLIENT", nombre="Cliente", descripcion="Opera solo con sus propios datos, puede ver interfaz de producto reducida"),
]

USERS_SEED = [
    {
        "nombre": "Admin", "apellido": "Sistema",
        "email": "admin@email.com", "password": "admin123",
        "rol_codigo": "ADMIN",
    },
    {
        "nombre": "Stock", "apellido": "Sistema",
        "email": "stock@email.com", "password": "stock123",
        "rol_codigo": "STOCK",
    },
    {
        "nombre": "Pedidos", "apellido": "Sistema",
        "email": "pedidos@email.com", "password": "pedidos123",
        "rol_codigo": "PEDIDOS",
    },
    {
        "nombre": "Cliente", "apellido": "Estandar",
        "email": "client@email.com", "password": "client123",
        "rol_codigo": "CLIENT",
    },
]


def seed_roles(session: Session):
    """Inserta roles si no existen ya (idempotente)."""
    for rol in ROLES_SEED:
        existing = session.exec(select(Rol).where(Rol.codigo == rol.codigo)).first()
        if not existing:
            session.add(rol)
    session.commit()


def seed_users(session: Session):
    """Crea usuarios de ejemplo con sus roles asignados (idempotente)."""
    for user_data in USERS_SEED:
        existing = session.exec(
            select(Usuario).where(Usuario.email == user_data["email"])
        ).first()
        if existing:
            continue  # ya existe, saltar

        nuevo = Usuario(
            nombre=user_data["nombre"],
            apellido=user_data["apellido"],
            email=user_data["email"],
            password_hash=get_password_hash(user_data["password"]),
        )
        session.add(nuevo)
        session.flush()  # para obtener el id

        # Asignar rol
        enlace = UsuarioRol(
            usuario_id=nuevo.id,
            rol_codigo=user_data["rol_codigo"],
        )
        session.add(enlace)

    session.commit()


def run_seed():
    """Run all seeds. Callable from lifespan."""
    engine = create_engine(DATABASE_URL, echo=False)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_roles(session)
        seed_users(session)


if __name__ == "__main__":
    run_seed()
