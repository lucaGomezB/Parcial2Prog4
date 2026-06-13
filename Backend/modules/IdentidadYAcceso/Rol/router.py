"""
Rol (Role) router module.

Defines read-only endpoints for role management under the /roles prefix.

Role listing is restricted to ADMIN users since role definitions are
sensitive system configuration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .schemas import RolRead
from . import service

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=list[RolRead],
            dependencies=[Depends(require_roles(["ADMIN"]))])
def read_roles(session: Session = Depends(get_session)):
    """
    GET /roles — List all roles.

    Restricted to ADMIN users. Returns the complete list
    of system roles (typically a small, static set).
    """
    return service.get_roles(session)


@router.get("/{codigo}", response_model=RolRead,
            dependencies=[Depends(require_roles(["ADMIN"]))])
def read_rol(codigo: str, session: Session = Depends(get_session)):
    """
    GET /roles/{codigo} — Get a single role by its semantic code.

    Restricted to ADMIN users. Returns 404 if not found.
    """
    rol = service.get_rol_by_codigo(session, codigo)
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return rol
