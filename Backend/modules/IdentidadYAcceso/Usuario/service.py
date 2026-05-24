import bcrypt
from sqlmodel import Session
from .models import Usuario
from .schemas import UsuarioCreate


def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def crear_usuario(session: Session, datos: UsuarioCreate) -> Usuario:
    nuevo_usuario = Usuario(
        nombre=datos.nombre,
        apellido=datos.apellido,
        email=datos.email,
        celular=datos.celular,
        password_hash=get_password_hash(datos.password),
    )
    session.add(nuevo_usuario)
    session.commit()
    session.refresh(nuevo_usuario)
    return nuevo_usuario
