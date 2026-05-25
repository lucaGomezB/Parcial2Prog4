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
    """Check if current user has ADMIN role."""
    return any(rol.codigo == "ADMIN" for rol in current_user.roles)


@router.get("/", response_model=List[DireccionEntregaRead])
def read_direcciones(
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """List all addresses for the current user. ADMIN sees all."""
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
    """Get a single address by ID. Owner-scoped for CLIENT users."""
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
    """Create a new delivery address for the authenticated user."""
    return DireccionEntregaService.create(session, data, usuario_id=current_user.id)


@router.patch("/{direccion_id}", response_model=DireccionEntregaRead)
def update_direccion(
    direccion_id: int,
    data: DireccionEntregaUpdate,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """Update address fields. Does NOT allow changing es_principal (use /principal endpoint)."""
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
    """Soft-delete a delivery address."""
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
    """Toggle an address as the principal delivery address.
    Unsets any existing principal for this user atomically.
    Idempotent: if already principal, returns unchanged.
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
