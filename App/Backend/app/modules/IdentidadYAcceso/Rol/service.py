"""
Rol (Role) service module.

Implements business logic for role management: create, list, update,
and delete operations, all wrapped in Unit of Work transactions.
"""

from sqlmodel import Session
from .models import Rol
from .schemas import RolCreate, RolUpdate
from ..uow import IdentidadYAccesoUnitOfWork


def create_rol(session: Session, data: RolCreate):
    """Create a new role with the provided data."""
    with IdentidadYAccesoUnitOfWork(session) as uow:
        db_rol = Rol.model_validate(data)
        uow.roles.create(db_rol)
        uow.roles.refresh(db_rol)
        return db_rol


def get_roles(session: Session):
    """Retrieve all roles (no pagination needed — small, fixed set)."""
    with IdentidadYAccesoUnitOfWork(session) as uow:
        return uow.roles.get_all()


def get_rol_by_codigo(session: Session, codigo: str) -> Rol | None:
    """Retrieve a single role by its semantic primary key (codigo).

    Uses the repository's get_by_codigo method which delegates
    to session.get() with the Rol model's semantic PK.
    Returns None if not found.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        return uow.roles.get_by_codigo(codigo)


def update_rol(session: Session, codigo: str, data: RolUpdate):
    """
    Partially update a role by its semantic code.

    Uses exclude_unset=True for PATCH semantics. Returns None
    if the role does not exist.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        db_rol = uow.roles.get_by_codigo(codigo)
        if not db_rol:
            return None
        values = data.model_dump(exclude_unset=True)
        for key, value in values.items():
            setattr(db_rol, key, value)
        uow.roles.update(db_rol)
        uow.roles.refresh(db_rol)
        return db_rol


def delete_rol(session: Session, codigo: str):
    """Delete a role by its semantic code. Returns None if not found."""
    with IdentidadYAccesoUnitOfWork(session) as uow:
        db_rol = uow.roles.get_by_codigo(codigo)
        if db_rol:
            uow.delete(db_rol)
        return db_rol
