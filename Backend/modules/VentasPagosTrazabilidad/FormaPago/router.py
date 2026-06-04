"""
FormaPago router — API endpoints for payment method management.

Prefix: /formas-pago

Access rules:
    GET  /          -> ADMIN, PEDIDOS (read)
    GET  /{code}    -> ADMIN, PEDIDOS (read)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import FormaPagoService
from .schemas import FormaPagoRead

router = APIRouter(prefix="/formas-pago", tags=["Formas de Pago"])


@router.get("/", response_model=List[FormaPagoRead],
            dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def read_all(incluir_deshabilitadas: bool = Query(False), session: Session = Depends(get_session)):
    """GET /formas-pago — List all payment methods.
    By default only enabled methods are shown. Requires ADMIN or PEDIDOS role."""
    return FormaPagoService.get_all(session, incluir_deshabilitadas=incluir_deshabilitadas)


@router.get("/{codigo}", response_model=FormaPagoRead,
            dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def read_one(codigo: str, session: Session = Depends(get_session)):
    """GET /formas-pago/{code} — Get a single payment method by its code.
    Requires ADMIN or PEDIDOS role."""
    obj = FormaPagoService.get_by_codigo(session, codigo)
    if not obj:
        raise HTTPException(status_code=404, detail="Forma de pago no encontrada")
    return obj
