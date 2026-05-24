from sqlmodel import Session, select
from .models import Rol
from .schemas import RolCreate, RolUpdate


def create_rol(session: Session, data: RolCreate):
    db_rol = Rol.model_validate(data)
    session.add(db_rol)
    session.commit()
    session.refresh(db_rol)
    return db_rol


def get_roles(session: Session):
    return session.exec(select(Rol)).all()


def update_rol(session: Session, codigo: str, data: RolUpdate):
    db_rol = session.get(Rol, codigo)
    if not db_rol:
        return None
    values = data.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(db_rol, key, value)
    session.add(db_rol)
    session.commit()
    session.refresh(db_rol)
    return db_rol


def delete_rol(session: Session, codigo: str):
    db_rol = session.get(Rol, codigo)
    if db_rol:
        session.delete(db_rol)
        session.commit()
    return db_rol
