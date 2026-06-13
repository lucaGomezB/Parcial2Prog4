"""
Pedido router — API endpoints for order management.

Request flow: HTTP -> FastAPI (Pydantic validation) -> Router -> Service -> DB
Response flow: DB -> Service -> Pydantic schema -> JSON

Auth:
    - require_roles(["ADMIN", "PEDIDOS"]) = restricted to admins/order managers
    - get_current_user = any authenticated user
    - No decorator = public access

Prefix: /pedidos
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from typing import List
from core.database import get_session
from core.paginated_response import PaginatedResponse
from modules.IdentidadYAcceso.Auth.dependencies import require_roles, get_current_user
from modules.IdentidadYAcceso.Usuario.models import Usuario
from .service import PedidoService
from .schemas import (
    PedidoRead, PedidoCreate, PedidoUpdate,
    PedidoAvanzarResponse, PedidoCancelarResponse,
    DetallePedidoUpdate,
    ValidarStockInput, ValidarStockResponse,
)
from ..HistorialEstadoPedido.service import HistorialEstadoPedidoService
from ..HistorialEstadoPedido.schemas import HistorialRead

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.get("/", response_model=PaginatedResponse[PedidoRead],
            dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def read_all(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
):
    """GET /pedidos — List ALL orders with pagination. Requires ADMIN or PEDIDOS role."""
    return PedidoService.get_all(session, skip=skip, limit=limit)


@router.get("/activos", response_model=PaginatedResponse[PedidoRead])
def read_activos(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """GET /pedidos/activos — List active (non-terminal) orders.

    ADMIN/PEDIDOS see all active orders; regular users only see their own.
    """
    es_gestor = any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles)
    if es_gestor:
        return PedidoService.get_activos(session, skip=skip, limit=limit)
    # Regular user: filter to their own active orders
    todos_activos = PedidoService.get_activos(session, skip=0, limit=10000)
    items_filtrados = [p for p in todos_activos.items if p.usuario_id == current_user.id]
    return PaginatedResponse(
        items=items_filtrados[skip:skip + limit],
        total=len(items_filtrados),
        skip=skip,
        limit=limit,
    )


@router.get("/historial", response_model=PaginatedResponse[PedidoRead])
def read_historial(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """GET /pedidos/historial — List terminal-state orders (ENTREGADO, CANCELADO).

    ADMIN/PEDIDOS see all history; regular users only see their own.
    """
    es_gestor = any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles)
    if es_gestor:
        return PedidoService.get_historial(session, skip=skip, limit=limit)
    return PedidoService.get_historial_by_usuario(session, current_user.id, skip=skip, limit=limit)


@router.get("/mis-pedidos", response_model=PaginatedResponse[PedidoRead])
def read_mis_pedidos(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """GET /pedidos/mis-pedidos — List orders belonging to the authenticated user.

    Used for the "My Orders" section in the customer profile.
    """
    return PedidoService.get_by_usuario_id(session, current_user.id, skip=skip, limit=limit)


@router.get("/{pedido_id}", response_model=PedidoRead)
def read_one(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """GET /pedidos/{id} — Get a single order by its ID.

    ADMIN/PEDIDOS can see any order; regular users can only see their own.
    """
    obj = PedidoService.get_by_id(session, pedido_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    # Regular users cannot view other users' orders
    if not any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles):
        if obj.usuario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este pedido")
    return obj


@router.get("/{pedido_id}/historial", response_model=List[HistorialRead])
def read_historial_pedido(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """GET /pedidos/{id}/historial — Get full state transition history for an order.

    ADMIN/PEDIDOS can see any order's history; regular users can only see their own.
    Returns the audit trail ordered from oldest to newest, with timestamps.
    """
    # First verify the order exists and user has access (same scoping as read_one)
    obj = PedidoService.get_by_id(session, pedido_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if not any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles):
        if obj.usuario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este pedido")

    return HistorialEstadoPedidoService.get_by_pedido(session, pedido_id)


@router.post("/", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def create(
    data: PedidoCreate,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """POST /pedidos — Create a new order.

    Logic:
    1. Forces the authenticated user as owner unless ADMIN/PEDIDOS supplies a different user_id
    2. Creates the order in PENDIENTE state with price/name snapshots
    3. Confirmation (PENDIENTE -> CONFIRMADO) happens ONLY via approved payment webhook

    Note: auto_confirmar was removed. Confirmation is exclusively via MercadoPago webhook.
    """
    if data.usuario_id is None:
        data.usuario_id = current_user.id

    pedido = PedidoService.create(session, data)
    return pedido


@router.get("/validar-stock", response_model=ValidarStockResponse)
def validar_stock(
    data: ValidarStockInput,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """GET /pedidos/validar-stock — Pre-validate stock availability for cart items.

    Read-only check — does NOT reserve or deduct stock.
    Used by the frontend cart to show real-time stock errors before order creation.
    """
    return PedidoService.validar_stock_items(session, data)


@router.patch("/{pedido_id}/avanzar", response_model=PedidoAvanzarResponse,
              dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def avanzar(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """PATCH /pedidos/{id}/avanzar — Advance the order to the next FSM state.

    Transitions:
        CONFIRMADO -> EN_PREP (preparation started)
        EN_PREP -> EN_CAMINO (out for delivery)
        EN_CAMINO -> ENTREGADO (delivered)

    NOTE: PENDIENTE -> CONFIRMADO is EXCLUSIVELY via payment webhook.
    This endpoint does NOT handle that transition anymore.

    Requires ADMIN or PEDIDOS role.
    """
    pedido, estado_anterior = PedidoService.avanzar_estado(session, pedido_id, current_user)
    return PedidoAvanzarResponse(
        id=pedido.id,
        estado_anterior=estado_anterior,
        estado_actual=pedido.estado_codigo,
        mensaje=f"Pedido avanzó de {estado_anterior} a {pedido.estado_codigo}",
    )


@router.patch("/{pedido_id}/cancelar", response_model=PedidoCancelarResponse)
def cancelar(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """PATCH /pedidos/{id}/cancelar — Cancel an order.

    Permission rules:
        ALL roles can only cancel orders in PENDIENTE or CONFIRMADO state.
        Cancelation is blocked for EN_PREP, EN_CAMINO, and terminal states.
    """
    pedido = PedidoService.cancelar_pedido(session, pedido_id, current_user)
    return PedidoCancelarResponse(
        id=pedido.id,
        estado_anterior=pedido.estado_codigo,
        estado_actual="CANCELADO",
        mensaje="Pedido cancelado",
    )


@router.patch("/{pedido_id}", response_model=PedidoRead,
              dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def update(pedido_id: int, data: PedidoUpdate, session: Session = Depends(get_session)):
    """PATCH /pedidos/{id} — Update order metadata and/or replace details.

    Metadata fields: direccion_id, forma_pago_codigo, notas.
    If `detalles` is provided, ALL existing detail lines are replaced
    with the new set (works only for PENDIENTE orders).
    Subtotal and total are recalculated automatically.

    Requires ADMIN or PEDIDOS role.
    """
    obj = PedidoService.update(session, pedido_id, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return obj


@router.patch("/{pedido_id}/detalles/{producto_id}", response_model=PedidoRead,
              dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def actualizar_detalle(
    pedido_id: int,
    producto_id: int,
    data: DetallePedidoUpdate,
    session: Session = Depends(get_session),
):
    """PATCH /pedidos/{id}/detalles/{producto_id} — Update or remove a detail line.

    cantidad=0 removes the detail line entirely.
    Only works on PENDIENTE orders (once CONFIRMADO, stock is already deducted).
    Recalculates subtotal and total after modification. Requires ADMIN or PEDIDOS role.
    """
    return PedidoService.actualizar_detalle(session, pedido_id, producto_id, data.cantidad)


@router.delete("/{pedido_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles(["ADMIN"]))])
def delete(pedido_id: int, session: Session = Depends(get_session)):
    """DELETE /pedidos/{id} — Soft-delete an order by its ID.

    The row remains in the database but is excluded from normal queries.
    Requires ADMIN role.
    """
    if not PedidoService.soft_delete(session, pedido_id):
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return None
