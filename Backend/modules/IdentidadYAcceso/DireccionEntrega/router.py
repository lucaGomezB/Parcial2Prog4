"""
DireccionEntrega (Delivery Address) router module.

Defines CRUD endpoints for user delivery addresses under the /direcciones prefix.

All endpoints require authentication (JWT). Regular users are scoped to
their own addresses; ADMIN users can access any address.

Endpoints:
- GET /direcciones: List user's addresses (ADMIN sees all).
- GET /direcciones/{id}: Get a specific address.
- POST /direcciones: Create a new address.
- PATCH /direcciones/{id}: Update address fields.
- DELETE /direcciones/{id}: Soft-delete an address.
- PATCH /direcciones/{id}/principal: Set as default address.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List

from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import get_current_user, require_roles
from modules.IdentidadYAcceso.Usuario.models import Usuario
from .service import DireccionEntregaService
from .schemas import DireccionEntregaRead, DireccionEntregaCreate, DireccionEntregaUpdate

router = APIRouter(prefix="/direcciones", tags=["Direcciones de Entrega"])


def _check_admin(current_user: Usuario) -> bool:
    """Check if the current user has ADMIN role for cross-user access."""
    return any(rol.codigo == "ADMIN" for rol in current_user.roles)


@router.get("/", response_model=List[DireccionEntregaRead])
def read_direcciones(
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """
    GET /direcciones — List delivery addresses for the current user.

    ADMIN users see all addresses across all users.
    Regular users see only their own addresses.
    """
    return DireccionEntregaService.get_all(
        session,
        usuario_id=current_user.id,
        es_admin=_check_admin(current_user),
    )


@router.get("/{direccion_id}", response_model=DireccionEntregaRead)
def read_direccion(
    direccion_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """
    GET /direcciones/{direccion_id} — Get a single delivery address by ID.

    Owner-scoped for CLIENT users (cannot access other users' addresses).
    """
    direccion = DireccionEntregaService.get_by_id(
        session,
        direccion_id=direccion_id,
        usuario_id=current_user.id,
        es_admin=_check_admin(current_user),
    )
    if not direccion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirección no encontrada")
    return direccion


@router.post("/", response_model=DireccionEntregaRead, status_code=status.HTTP_201_CREATED)
def create_direccion(
    data: DireccionEntregaCreate,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """
    POST /direcciones — Create a new delivery address for the authenticated user.

    If es_principal=True, any existing principal address is automatically unset.
    """
    return DireccionEntregaService.create(session, data, usuario_id=current_user.id)


@router.patch("/{direccion_id}", response_model=DireccionEntregaRead)
def update_direccion(
    direccion_id: int,
    data: DireccionEntregaUpdate,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """
    PATCH /direcciones/{direccion_id} — Update address fields.

    Does NOT allow changing es_principal via this endpoint
    (use PATCH /direcciones/{id}/principal instead).
    """
    direccion = DireccionEntregaService.update(
        session,
        direccion_id=direccion_id,
        data=data,
        usuario_id=current_user.id,
        es_admin=_check_admin(current_user),
    )
    if not direccion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirección no encontrada")
    return direccion


@router.delete("/{direccion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_direccion(
    direccion_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """
    DELETE /direcciones/{direccion_id} — Soft-delete a delivery address.

    Sets deleted_at timestamp. The record is preserved in the database
    for historical order references.
    """
    deleted = DireccionEntregaService.soft_delete(
        session,
        direccion_id=direccion_id,
        usuario_id=current_user.id,
        es_admin=_check_admin(current_user),
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirección no encontrada")
    return None


@router.patch("/{direccion_id}/principal", response_model=DireccionEntregaRead)
def set_principal_direccion(
    direccion_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """
    PATCH /direcciones/{direccion_id}/principal — Set an address as the default.

    Atomically unsets any existing principal for the same user.
    Idempotent: if already principal, returns the address unchanged.
    """
    direccion = DireccionEntregaService.set_principal(
        session,
        direccion_id=direccion_id,
        usuario_id=current_user.id,
        es_admin=_check_admin(current_user),
    )
    if not direccion:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dirección no encontrada")
    return direccion
