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
    """List all payment methods. Optionally include disabled ones. Public endpoint, no auth required."""
    return FormaPagoService.get_all(session, incluir_deshabilitadas=incluir_deshabilitadas)


@router.get("/{codigo}", response_model=FormaPagoRead)
def read_one(codigo: str, session: Session = Depends(get_session)):
    """Get a single payment method by its code. Public endpoint, no auth required."""
    obj = FormaPagoService.get_by_codigo(session, codigo)
    if not obj:
        raise HTTPException(status_code=404, detail="Forma de pago no encontrada")
    return obj


@router.post("/", response_model=FormaPagoRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(["ADMIN"]))])
def create(data: FormaPagoCreate, session: Session = Depends(get_session)):
    """Create a new payment method. Requires ADMIN role."""
    return FormaPagoService.create(session, data)


@router.patch("/{codigo}", response_model=FormaPagoRead,
              dependencies=[Depends(require_roles(["ADMIN"]))])
def update(codigo: str, data: FormaPagoUpdate, session: Session = Depends(get_session)):
    """Update an existing payment method by its code. Requires ADMIN role."""
    obj = FormaPagoService.update(session, codigo, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Forma de pago no encontrada")
    return obj


@router.delete("/{codigo}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(["ADMIN"]))])
def delete(codigo: str, session: Session = Depends(get_session)):
    """Delete a payment method by its code. Requires ADMIN role."""
    if not FormaPagoService.delete(session, codigo):
        raise HTTPException(status_code=404, detail="Forma de pago no encontrada")
    return None
