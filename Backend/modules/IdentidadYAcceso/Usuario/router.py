from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session
from typing import Optional, List
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .schemas import UsuarioCreate, UsuarioRead, UsuarioReadWithRoles, UsuarioUpdateWithRoles
from . import service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=UsuarioRead, dependencies=[Depends(require_roles(["ADMIN"]))])
def create_user(datos: UsuarioCreate, session: Session = Depends(get_session)):
    """Create a new user with the provided data. Requires ADMIN role."""
    return service.crear_usuario(session, datos)


@router.get("/", response_model=List[UsuarioReadWithRoles],
            dependencies=[Depends(require_roles(["ADMIN"]))])
def list_usuarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    rol_codigo: Optional[str] = Query(None, description="Filter by role code (e.g., ADMIN, CLIENT)"),
    session: Session = Depends(get_session),
):
    """List users with pagination and optional role filter. Each user includes roles. ADMIN only."""
    return service.listar_usuarios(session, skip=skip, limit=limit, rol_codigo=rol_codigo)


@router.get("/{usuario_id}", response_model=UsuarioReadWithRoles,
            dependencies=[Depends(require_roles(["ADMIN"]))])
def get_usuario(usuario_id: int, session: Session = Depends(get_session)):
    """Get a single user by ID with roles included. ADMIN only."""
    usuario = service.obtener_usuario(session, usuario_id)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


@router.patch("/{usuario_id}", response_model=UsuarioReadWithRoles,
              dependencies=[Depends(require_roles(["ADMIN"]))])
def update_usuario(
    usuario_id: int,
    datos: UsuarioUpdateWithRoles,
    session: Session = Depends(get_session),
):
    """Update user fields and/or reassign roles. ADMIN only.
    Send `roles_codigos: [...]` to replace all roles. Omit to keep current roles."""
    usuario = service.actualizar_usuario(session, usuario_id, datos)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(["ADMIN"]))])
def delete_usuario(usuario_id: int, session: Session = Depends(get_session)):
    """Soft-delete a user. ADMIN only."""
    if not service.eliminar_usuario(session, usuario_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return None
