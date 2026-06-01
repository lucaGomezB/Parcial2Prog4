"""
Rol (Role) router module.

Defines CRUD endpoints for role management under the /roles prefix.

Role listing is accessible to any authenticated user (for UI dropdowns
and permission checks). Write operations (create, update, delete) are
restricted to ADMIN users.
"""

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
    """
    GET /roles — List all roles.

    Accessible to any authenticated user. Returns the complete list
    of system roles (typically a small, static set).
    """
    return service.get_roles(session)


@router.get("/{codigo}", response_model=RolRead)
def read_rol(codigo: str, session: Session = Depends(get_session)):
    """
    GET /roles/{codigo} — Get a single role by its semantic code.

    Accessible to any authenticated user. Returns 404 if not found.
    """
    rol = session.get(Rol, codigo)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return rol


@router.post("/", response_model=RolRead, dependencies=[Depends(require_roles(["ADMIN"]))])
def create_rol(data: RolCreate, session: Session = Depends(get_session)):
    """
    POST /roles — Create a new role.

    Requires ADMIN role. Accepts code, name, and optional description.
    """
    return service.create_rol(session, data)


@router.patch("/{codigo}", response_model=RolRead, dependencies=[Depends(require_roles(["ADMIN"]))])
def update_rol(codigo: str, data: RolUpdate, session: Session = Depends(get_session)):
    """
    PATCH /roles/{codigo} — Partially update an existing role.

    Requires ADMIN role. All fields optional. Returns 404 if not found.
    """
    rol = service.update_rol(session, codigo, data)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return rol


@router.delete("/{codigo}", dependencies=[Depends(require_roles(["ADMIN"]))])
def delete_rol(codigo: str, session: Session = Depends(get_session)):
    """
    DELETE /roles/{codigo} — Delete a role by its semantic code.

    Requires ADMIN role. Returns 404 if not found. Note: deleting a
    role sets rol_codigo to NULL in UsuarioRol (SET NULL ondelete).
    """
    if not service.delete_rol(session, codigo):
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return {"message": "Rol eliminado correctamente"}
