from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .models import Rol
from .schemas import RolCreate, RolRead, RolUpdate
from . import service

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RolRead])
def read_roles(session: Session = Depends(get_session)):
    return service.get_roles(session)


@router.get("/{codigo}", response_model=RolRead)
def read_rol(codigo: str, session: Session = Depends(get_session)):
    rol = session.get(Rol, codigo)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return rol


@router.post("/", response_model=RolRead, dependencies=[Depends(require_roles(["ADMIN"]))])
def create_rol(data: RolCreate, session: Session = Depends(get_session)):
    return service.create_rol(session, data)


@router.patch("/{codigo}", response_model=RolRead, dependencies=[Depends(require_roles(["ADMIN"]))])
def update_rol(codigo: str, data: RolUpdate, session: Session = Depends(get_session)):
    rol = service.update_rol(session, codigo, data)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return rol


@router.delete("/{codigo}", dependencies=[Depends(require_roles(["ADMIN"]))])
def delete_rol(codigo: str, session: Session = Depends(get_session)):
    if not service.delete_rol(session, codigo):
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return {"message": "Rol eliminado correctamente"}
