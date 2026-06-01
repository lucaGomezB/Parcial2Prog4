"""
FormaPago router — API endpoints for payment method management.

Prefix: /formas-pago

Access rules:
    GET  /          -> public (read, enabled only by default)
    GET  /{code}    -> public (read)
    POST /          -> ADMIN only
    PATCH /{code}   -> ADMIN only
    DELETE /{code}  -> ADMIN only
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import FormaPagoService
from .schemas import FormaPagoRead, FormaPagoCreate, FormaPagoUpdate

router = APIRouter(prefix="/formas-pago", tags=["Formas de Pago"])


@router.get("/", response_model=List[FormaPagoRead])
def read_all(incluir_deshabilitadas: bool = Query(False), session: Session = Depends(get_session)):
    """GET /formas-pago — List all payment methods.
    By default only enabled methods are shown. Public endpoint, no auth required."""
    return FormaPagoService.get_all(session, incluir_deshabilitadas=incluir_deshabilitadas)


@router.get("/{codigo}", response_model=FormaPagoRead)
def read_one(codigo: str, session: Session = Depends(get_session)):
    """GET /formas-pago/{code} — Get a single payment method by its code. Public endpoint."""
    obj = FormaPagoService.get_by_codigo(session, codigo)
    if not obj:
        raise HTTPException(status_code=404, detail="Forma de pago no encontrada")
    return obj


@router.post("/", response_model=FormaPagoRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(["ADMIN"]))])
def create(data: FormaPagoCreate, session: Session = Depends(get_session)):
    """POST /formas-pago — Create a new payment method. Requires ADMIN role."""
    return FormaPagoService.create(session, data)


@router.patch("/{codigo}", response_model=FormaPagoRead,
              dependencies=[Depends(require_roles(["ADMIN"]))])
def update(codigo: str, data: FormaPagoUpdate, session: Session = Depends(get_session)):
    """PATCH /formas-pago/{code} — Update an existing payment method by code. Requires ADMIN role."""
    obj = FormaPagoService.update(session, codigo, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Forma de pago no encontrada")
    return obj


@router.delete("/{codigo}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(["ADMIN"]))])
def delete(codigo: str, session: Session = Depends(get_session)):
    """DELETE /formas-pago/{code} — Delete a payment method by code. Requires ADMIN role.
    Cannot delete if referenced by existing orders (FK constraint)."""
    if not FormaPagoService.delete(session, codigo):
        raise HTTPException(status_code=404, detail="Forma de pago no encontrada")
    return None
