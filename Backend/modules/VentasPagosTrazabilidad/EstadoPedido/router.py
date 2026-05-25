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
    return EstadoPedidoService.get_all(session)


@router.get("/{codigo}", response_model=EstadoPedidoRead)
def read_one(codigo: str, session: Session = Depends(get_session)):
    obj = EstadoPedidoService.get_by_codigo(session, codigo)
    if not obj:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return obj


@router.post("/", response_model=EstadoPedidoRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles(["ADMIN"]))])
def create(data: EstadoPedidoCreate, session: Session = Depends(get_session)):
    return EstadoPedidoService.create(session, data)


@router.patch("/{codigo}", response_model=EstadoPedidoRead,
              dependencies=[Depends(require_roles(["ADMIN"]))])
def update(codigo: str, data: EstadoPedidoUpdate, session: Session = Depends(get_session)):
    obj = EstadoPedidoService.update(session, codigo, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return obj


@router.delete("/{codigo}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(["ADMIN"]))])
def delete(codigo: str, session: Session = Depends(get_session)):
    if not EstadoPedidoService.delete(session, codigo):
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return None
