from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import EstadoPedidoService
from .schemas import EstadoPedidoRead

router = APIRouter(prefix="/estados-pedido", tags=["Estados de Pedido"])


@router.get("/", response_model=List[EstadoPedidoRead],
            dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def read_all(session: Session = Depends(get_session)):
    """List all order statuses. Requires ADMIN or PEDIDOS role."""
    return EstadoPedidoService.get_all(session)


@router.get("/{codigo}", response_model=EstadoPedidoRead,
            dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def read_one(codigo: str, session: Session = Depends(get_session)):
    """Get a single order status by its code. Requires ADMIN or PEDIDOS role."""
    obj = EstadoPedidoService.get_by_codigo(session, codigo)
    if not obj:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return obj
