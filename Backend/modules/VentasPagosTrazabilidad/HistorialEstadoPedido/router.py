"""
HistorialEstadoPedido router — read-only API endpoints for order state history.

Prefix: /historial-estado

Endpoints:
    GET /                          -> paginated list, optional pedido_id filter
    GET /{historial_id}            -> single entry by PK

All endpoints require ADMIN or PEDIDOS role (audit data is sensitive).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from typing import List, Optional
from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles
from .service import HistorialEstadoPedidoService
from .schemas import HistorialRead

router = APIRouter(prefix="/historial-estado", tags=["Historial de Estados"])


@router.get(
    "/",
    response_model=List[HistorialRead],
    dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))],
)
def read_all(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    pedido_id: Optional[int] = Query(None),
    session: Session = Depends(get_session),
):
    """GET /historial-estado — List history entries.

    Supports pagination with skip/limit and optional filtering by pedido_id.
    Results are ordered by created_at DESC (newest first).

    Requires ADMIN or PEDIDOS role.
    """
    return HistorialEstadoPedidoService.get_all(
        session, skip=skip, limit=limit, pedido_id=pedido_id
    )


@router.get(
    "/{historial_id}",
    response_model=HistorialRead,
    dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))],
)
def read_one(
    historial_id: int,
    session: Session = Depends(get_session),
):
    """GET /historial-estado/{id} — Get a single history entry by its PK.

    Requires ADMIN or PEDIDOS role.
    Returns 404 if the entry does not exist.
    """
    obj = HistorialEstadoPedidoService.get_by_id(session, historial_id)
    if not obj:
        raise HTTPException(
            status_code=404,
            detail="Registro de historial no encontrado",
        )
    return obj
