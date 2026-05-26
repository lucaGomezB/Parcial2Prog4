from sqlmodel import Session
from .models import Rol
from .schemas import RolCreate, RolUpdate
from ..uow import IdentidadYAccesoUnitOfWork


def create_rol(session: Session, data: RolCreate):
    with IdentidadYAccesoUnitOfWork(session) as uow:
        db_rol = Rol.model_validate(data)
        uow.roles.add(db_rol)
        uow.commit()
        uow.roles.refresh(db_rol)
        return db_rol


def get_roles(session: Session):
    with IdentidadYAccesoUnitOfWork(session) as uow:
        return uow.roles.get_all()


def update_rol(session: Session, codigo: str, data: RolUpdate):
    with IdentidadYAccesoUnitOfWork(session) as uow:
        db_rol = uow.roles.get_by_codigo(codigo)
        if not db_rol:
            return None
        values = data.model_dump(exclude_unset=True)
        for key, value in values.items():
            setattr(db_rol, key, value)
        uow.roles.add(db_rol)
        uow.roles.refresh(db_rol)
        return db_rol


def delete_rol(session: Session, codigo: str):
    with IdentidadYAccesoUnitOfWork(session) as uow:
        db_rol = uow.roles.get_by_codigo(codigo)
        if db_rol:
            uow.session.delete(db_rol)
        return db_rol
