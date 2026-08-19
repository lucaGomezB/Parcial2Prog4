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
from app.core.database import get_session
from app.core.paginated_response import PaginatedResponse
from app.core.dependencies import AdminOnly
from app.core.routing import get_or_404
from app.modules.IdentidadYAcceso.Auth.dependencies import require_roles, get_current_user
from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from .schemas import UsuarioCreate, UsuarioRead, UsuarioReadWithRoles, UsuarioUpdateWithRoles
from . import service

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED,
            dependencies=[Depends(require_roles(AdminOnly))])
def create_user(
    datos: UsuarioCreate,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """
    POST /usuarios — Create a new user with the provided data.

    Requires ADMIN role. Use /auth/register for self-registration.
    """
    return service.crear_usuario(session, datos, admin_id=current_user.id)


@router.get("/", response_model=PaginatedResponse[UsuarioReadWithRoles],
            dependencies=[Depends(require_roles(AdminOnly))])
def list_usuarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    incluir_eliminados: bool = Query(False, description="Incluir usuarios soft-deleteados (solo ADMIN)"),
    rol_codigo: Optional[str] = Query(None, description="Filter by role code (e.g., ADMIN, CLIENT)"),
    search: Optional[str] = Query(None, description="Busqueda textual por nombre, apellido o email"),
    session: Session = Depends(get_session),
):
    """
    GET /usuarios — List users with pagination and optional filters.

    Paginated: skip (offset) and limit (max 500) prevent unbounded queries.
    Optional rol_codigo filters users by a specific role.
    Optional search performs ILIKE matching on nombre, apellido, and email.
    Optional incluir_eliminados includes soft-deleted records (ADMIN only).
    Returns each user with their assigned roles. ADMIN only.
    """
    return service.listar_usuarios(session, skip=skip, limit=limit, rol_codigo=rol_codigo, search=search, incluir_eliminados=incluir_eliminados)


@router.get("/{usuario_id}", response_model=UsuarioReadWithRoles,
            dependencies=[Depends(require_roles(AdminOnly))])
def get_usuario(
    usuario_id: int,
    incluir_eliminados: bool = Query(False, description="Incluir usuarios soft-deleteados (solo ADMIN)"),
    session: Session = Depends(get_session),
):
    """
    GET /usuarios/{usuario_id} — Get a single user by ID with roles.

    Returns 404 if the user does not exist or has been soft-deleted. ADMIN only.
    """
    usuario = service.obtener_usuario(session, usuario_id, incluir_eliminados=incluir_eliminados)
    return get_or_404(usuario, "Usuario no encontrado")


@router.patch("/{usuario_id}", response_model=UsuarioReadWithRoles,
              dependencies=[Depends(require_roles(AdminOnly))])
def update_usuario(
    usuario_id: int,
    datos: UsuarioUpdateWithRoles,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """
    PATCH /usuarios/{usuario_id} — Partially update user fields and/or reassign role.

    Send only the fields to change. To reassign the role, send roles_codigos with
    a single role code (e.g., "CLIENT"). A user can only have ONE role. ADMIN only.
    """
    usuario = service.actualizar_usuario(session, usuario_id, datos, admin_id=current_user.id)
    return get_or_404(usuario, "Usuario no encontrado")


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(AdminOnly))])
def delete_usuario(usuario_id: int, session: Session = Depends(get_session)):
    """
    DELETE /usuarios/{usuario_id} — Soft-delete a user.

    Sets deleted_at timestamp (logical deletion). The user record is
    preserved in the database for referential integrity with historical
    orders. Returns 204 No Content on success. ADMIN only.
    """
    get_or_404(service.eliminar_usuario(session, usuario_id), "Usuario no encontrado")
    return None
