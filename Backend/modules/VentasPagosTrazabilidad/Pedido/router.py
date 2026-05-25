from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles, get_current_user
from modules.IdentidadYAcceso.Usuario.models import Usuario
from .service import PedidoService
from .schemas import PedidoRead, PedidoCreate, PedidoUpdate

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.get("/", response_model=List[PedidoRead],
            dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def read_all(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
):
    return PedidoService.get_all(session, skip=skip, limit=limit)


@router.get("/mis-pedidos", response_model=List[PedidoRead])
def read_mis_pedidos(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    return PedidoService.get_by_usuario_id(session, current_user.id, skip=skip, limit=limit)


@router.get("/{pedido_id}", response_model=PedidoRead)
def read_one(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    obj = PedidoService.get_by_id(session, pedido_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # Clientes solo ven sus propios pedidos
    if not any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles):
        if obj.usuario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este pedido")
    return obj


@router.post("/", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def create(
    data: PedidoCreate,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    # Forzar usuario autenticado como dueño del pedido
    if not any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles):
        data.usuario_id = current_user.id
    return PedidoService.create(session, data)


@router.patch("/{pedido_id}", response_model=PedidoRead,
              dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def update(pedido_id: int, data: PedidoUpdate, session: Session = Depends(get_session)):
    obj = PedidoService.update(session, pedido_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return obj


@router.delete("/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(["ADMIN"]))])
def delete(pedido_id: int, session: Session = Depends(get_session)):
    if not PedidoService.soft_delete(session, pedido_id):
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return None
