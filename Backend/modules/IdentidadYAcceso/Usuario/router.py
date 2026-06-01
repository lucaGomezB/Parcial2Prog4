"""
Usuario (User) router module.

Defines CRUD endpoints for user management under the /usuarios prefix.

All endpoints require ADMIN role for security — regular users manage
their own profile via /auth/register and /auth/me endpoints.

Endpoints:
- POST /usuarios: Create a new user (ADMIN).
- GET /usuarios: List users with pagination and role filter (ADMIN).
- GET /usuarios/{id}: Get a single user by ID (ADMIN).
- PATCH /usuarios/{id}: Partially update a user (ADMIN).
- DELETE /usuarios/{id}: Soft-delete a user (ADMIN).
"""

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
    """
    POST /usuarios — Create a new user with the provided data.

    Requires ADMIN role. Use /auth/register for self-registration.
    """
    return service.crear_usuario(session, datos)


@router.get("/", response_model=List[UsuarioReadWithRoles],
            dependencies=[Depends(require_roles(["ADMIN"]))])
def list_usuarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    rol_codigo: Optional[str] = Query(None, description="Filter by role code (e.g., ADMIN, CLIENT)"),
    session: Session = Depends(get_session),
):
    """
    GET /usuarios — List users with pagination and optional role filter.

    Paginated: skip (offset) and limit (max 500) prevent unbounded queries.
    Optional rol_codigo filters users by a specific role.
    Returns each user with their assigned roles. ADMIN only.
    """
    return service.listar_usuarios(session, skip=skip, limit=limit, rol_codigo=rol_codigo)


@router.get("/{usuario_id}", response_model=UsuarioReadWithRoles,
            dependencies=[Depends(require_roles(["ADMIN"]))])
def get_usuario(usuario_id: int, session: Session = Depends(get_session)):
    """
    GET /usuarios/{usuario_id} — Get a single user by ID with roles.

    Returns 404 if the user does not exist or has been soft-deleted. ADMIN only.
    """
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
    """
    PATCH /usuarios/{usuario_id} — Partially update user fields and/or reassign roles.

    Send only the fields to change. To reassign roles, send roles_codigos.
    To remove all roles, send roles_codigos: []. ADMIN only.
    """
    usuario = service.actualizar_usuario(session, usuario_id, datos)
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return usuario


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(["ADMIN"]))])
def delete_usuario(usuario_id: int, session: Session = Depends(get_session)):
    """
    DELETE /usuarios/{usuario_id} — Soft-delete a user.

    Sets deleted_at timestamp (logical deletion). The user record is
    preserved in the database for referential integrity with historical
    orders. Returns 204 No Content on success. ADMIN only.
    """
    if not service.eliminar_usuario(session, usuario_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return None
