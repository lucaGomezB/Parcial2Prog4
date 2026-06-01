"""
EstadoPedido router — API endpoints for order status catalog management.

Prefix: /estados-pedido

Access rules:
    GET  /          -> public (read)
    GET  /{code}    -> public (read)
    POST /          -> ADMIN only
    PATCH /{code}   -> ADMIN only
    DELETE /{code}  -> ADMIN only
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import EstadoPedidoService
from .schemas import EstadoPedidoRead, EstadoPedidoCreate, EstadoPedidoUpdate

router = APIRouter(prefix="/estados-pedido", tags=["Estados de Pedido"])


@router.get("/", response_model=List[EstadoPedidoRead])
def read_all(session: Session = Depends(get_session)):
    """GET /estados-pedido — List all order statuses. Public endpoint, no auth required."""
    return EstadoPedidoService.get_all(session)


@router.get("/{codigo}", response_model=EstadoPedidoRead)
def read_one(codigo: str, session: Session = Depends(get_session)):
    """GET /estados-pedido/{code} — Get a single order status by its code. Public endpoint."""
    obj = EstadoPedidoService.get_by_codigo(session, codigo)
    if not obj:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return obj


@router.post("/", response_model=EstadoPedidoRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(["ADMIN"]))])
def create(data: EstadoPedidoCreate, session: Session = Depends(get_session)):
    """POST /estados-pedido — Create a new order status. Requires ADMIN role."""
    return EstadoPedidoService.create(session, data)


@router.patch("/{codigo}", response_model=EstadoPedidoRead,
              dependencies=[Depends(require_roles(["ADMIN"]))])
def update(codigo: str, data: EstadoPedidoUpdate, session: Session = Depends(get_session)):
    """PATCH /estados-pedido/{code} — Update an existing order status by code. Requires ADMIN role."""
    obj = EstadoPedidoService.update(session, codigo, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return obj


@router.delete("/{codigo}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(["ADMIN"]))])
def delete(codigo: str, session: Session = Depends(get_session)):
    """DELETE /estados-pedido/{code} — Delete an order status by code. Requires ADMIN role.

    Cannot delete if referenced by existing orders (FK constraint).
    """
    if not EstadoPedidoService.delete(session, codigo):
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return None
