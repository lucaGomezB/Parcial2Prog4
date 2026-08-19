"""
FormaPago router — API endpoints for payment method management.

Prefix: /formas-pago

Access rules:
    GET  /          -> All authenticated users (CLIENT sees only habilitado=True)
    GET  /{code}    -> ADMIN, PEDIDOS (read)
    PATCH /{code}   -> ADMIN (toggle habilitado)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List
from app.core.database import get_session
from app.core.dependencies import AdminOrPedidos, AdminOnly
from app.core.routing import get_or_404
from app.modules.IdentidadYAcceso.Auth.dependencies import require_roles, get_current_user
from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from .service import FormaPagoService
from .schemas import FormaPagoRead, FormaPagoUpdate

router = APIRouter(prefix="/formas-pago", tags=["Formas de Pago"])


@router.get("/", response_model=List[FormaPagoRead])
def read_all(
    incluir_deshabilitadas: bool = Query(False),
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """GET /formas-pago — List all payment methods.

    Authenticated users can access this endpoint. CLIENT users always see
    only habilitado=True methods regardless of the incluir_deshabilitadas
    query parameter. ADMIN and PEDIDOS users can override the filter."""
    user_roles = [r.codigo for r in current_user.roles]
    is_staff = "ADMIN" in user_roles or "PEDIDOS" in user_roles
    # CLIENT users NEVER see disabled methods — force filter
    if not is_staff:
        incluir_deshabilitadas = False
    return FormaPagoService.get_all(session, incluir_deshabilitadas=incluir_deshabilitadas)


@router.get("/{codigo}", response_model=FormaPagoRead,
            dependencies=[Depends(require_roles(AdminOrPedidos))])
def read_one(codigo: str, session: Session = Depends(get_session)):
    """GET /formas-pago/{code} — Get a single payment method by its code.
    Requires ADMIN or PEDIDOS role."""
    obj = FormaPagoService.get_by_codigo(session, codigo)
    return get_or_404(obj, "Forma de pago no encontrada")


@router.patch("/{codigo}", response_model=FormaPagoRead,
              dependencies=[Depends(require_roles(AdminOnly))])
def toggle_habilitado(codigo: str, data: FormaPagoUpdate, session: Session = Depends(get_session)):
    """PATCH /formas-pago/{code} — Update a payment method (e.g., toggle habilitado).
    Requires ADMIN role."""
    obj = FormaPagoService.update(session, codigo, data)
    return get_or_404(obj, "Forma de pago no encontrada")
