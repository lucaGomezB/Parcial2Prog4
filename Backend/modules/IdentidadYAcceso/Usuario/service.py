import bcrypt
from typing import List, Optional
from fastapi import HTTPException, status
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from .models import Usuario
from .schemas import UsuarioCreate, UsuarioUpdateWithRoles
from ..Rol.models import Rol
from ..uow import IdentidadYAccesoUnitOfWork


def get_password_hash(password: str) -> str:
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def crear_usuario(session: Session, datos: UsuarioCreate) -> Usuario:
    with IdentidadYAccesoUnitOfWork(session) as uow:
        nuevo_usuario = Usuario(
            nombre=datos.nombre,
            apellido=datos.apellido,
            email=datos.email,
            celular=datos.celular,
            password_hash=get_password_hash(datos.password),
        )
        uow.usuarios.add(nuevo_usuario)
        uow.flush()

        # Assign roles if provided
        if datos.roles_codigos:
            for codigo in datos.roles_codigos:
                rol = uow.roles.get_by_id(codigo)
                if rol:
                    nuevo_usuario.roles.append(rol)

        uow.commit()
        uow.usuarios.refresh(nuevo_usuario)
        return _load_roles(session, nuevo_usuario)


def _load_roles(session: Session, usuario: Usuario):
    """Eager-load roles relationship so they're available after commit."""
    session.exec(
        select(Usuario)
        .where(Usuario.id == usuario.id)
        .options(selectinload(Usuario.roles))
    ).first()
    return usuario


def listar_usuarios(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    rol_codigo: Optional[str] = None,
) -> List[Usuario]:
    """List users with optional role filter and eager-loaded roles."""
    with IdentidadYAccesoUnitOfWork(session) as uow:
        if rol_codigo:
            return uow.usuarios.get_all_by_role(rol_codigo, skip=skip, limit=limit)
        # Use the base get_all which filters soft-deleted
        return uow.usuarios.get_all(skip=skip, limit=limit)


def obtener_usuario(session: Session, usuario_id: int) -> Optional[Usuario]:
    """Get a single user by ID with eager-loaded roles.
    Returns None if soft-deleted or not found."""
    with IdentidadYAccesoUnitOfWork(session) as uow:
        # Custom query with selectinload for roles
        stmt = (
            select(Usuario)
            .where(Usuario.id == usuario_id)
            .options(selectinload(Usuario.roles))
        )
        return uow.session.exec(stmt).first()


def actualizar_usuario(
    session: Session,
    usuario_id: int,
    datos: UsuarioUpdateWithRoles,
) -> Optional[Usuario]:
    """Update user fields and/or reassign roles. Returns None if not found."""
    with IdentidadYAccesoUnitOfWork(session) as uow:
        usuario = uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            return None

        # Update scalar fields
        values = datos.model_dump(exclude_unset=True, exclude={"roles_codigos"})
        for key, value in values.items():
            setattr(usuario, key, value)
        uow.usuarios.add(usuario)

        # Reassign roles if provided
        if datos.roles_codigos is not None:
            usuario.roles = []
            for codigo in datos.roles_codigos:
                rol = uow.roles.get_by_id(codigo)
                if rol:
                    usuario.roles.append(rol)

        uow.commit()
        return _load_roles(session, usuario)


def eliminar_usuario(session: Session, usuario_id: int) -> bool:
    """Soft-delete a user. Returns False if not found."""
    with IdentidadYAccesoUnitOfWork(session) as uow:
        usuario = uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            return False
        from models.base import get_utc_now
        usuario.deleted_at = get_utc_now()
        uow.usuarios.add(usuario)
        uow.commit()
        return True
