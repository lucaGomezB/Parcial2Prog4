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
from modules.IdentidadYAcceso.Auth.dependencies import require_roles, get_current_user
from modules.IdentidadYAcceso.Usuario.models import Usuario
from .service import PedidoService
from .schemas import (
    PedidoRead, PedidoCreate, PedidoUpdate,
    PedidoAvanzarResponse, PedidoCancelarResponse,
    DetallePedidoUpdate,
    ValidarStockInput, ValidarStockResponse,
)

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])


@router.get("/", response_model=List[PedidoRead],
            dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def read_all(
    skip: int = Query(0),
    limit: int = Query(100),
    session: Session = Depends(get_session),
):
    """GET /pedidos — List ALL orders with pagination. Requires ADMIN or PEDIDOS role."""
    return PedidoService.get_all(session, skip=skip, limit=limit)


@router.get("/activos", response_model=List[PedidoRead])
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
    return [p for p in todos_activos if p.usuario_id == current_user.id][skip:skip + limit]


@router.get("/historial", response_model=List[PedidoRead])
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


@router.get("/mis-pedidos", response_model=List[PedidoRead])
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


@router.post("/", response_model=PedidoRead, status_code=status.HTTP_201_CREATED)
def create(
    data: PedidoCreate,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
    auto_confirmar: bool = Query(True, description="Auto-advance to CONFIRMADO for client users"),
):
    """POST /pedidos — Create a new order.

    Logic:
    1. Forces the authenticated user as owner unless ADMIN/PEDIDOS supplies a different user_id
    2. Creates the order in PENDIENTE state with price/name snapshots
    3. If auto_confirmar=True (default) and user is NOT a manager,
       automatically advances the order to CONFIRMADO (deducts stock).

    Why auto_confirmar? Customers want their order confirmed immediately.
    Managers can set auto_confirmar=False to leave it in PENDIENTE for manual review.
    """
    es_gestor = any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles)

    if data.usuario_id is None:
        data.usuario_id = current_user.id

    pedido = PedidoService.create(session, data)

    # Auto-advance to CONFIRMADO for client users (deducts stock)
    if not es_gestor and auto_confirmar:
        try:
            pedido, _ = PedidoService.avanzar_estado(session, pedido.id, current_user)
        except HTTPException:
            raise
        except Exception:
            # If auto-advance fails for non-HTTP reasons, the order stays in PENDIENTE
            pass

    return pedido


@router.post("/validar-stock", response_model=ValidarStockResponse)
def validar_stock(
    data: ValidarStockInput,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """POST /pedidos/validar-stock — Pre-validate stock availability for cart items.

    Read-only check — does NOT reserve or deduct stock.
    Used by the frontend cart to show real-time stock errors before order creation.
    """
    return PedidoService.validar_stock_items(session, data)


@router.post("/{pedido_id}/avanzar", response_model=PedidoAvanzarResponse,
             dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def avanzar(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """POST /pedidos/{id}/avanzar — Advance the order to the next FSM state.

    Transitions:
        PENDIENTE -> CONFIRMADO (deducts stock)
        CONFIRMADO -> EN_PREP (preparation started)
        EN_PREP -> EN_CAMINO (out for delivery)
        EN_CAMINO -> ENTREGADO (delivered)

    Requires ADMIN or PEDIDOS role.
    """
    pedido, estado_anterior = PedidoService.avanzar_estado(session, pedido_id, current_user)
    return PedidoAvanzarResponse(
        id=pedido.id,
        estado_anterior=estado_anterior,
        estado_actual=pedido.estado_codigo,
        mensaje=f"Pedido avanzó de {estado_anterior} a {pedido.estado_codigo}",
    )


@router.post("/{pedido_id}/cancelar", response_model=PedidoCancelarResponse)
def cancelar(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """POST /pedidos/{id}/cancelar — Cancel an order.

    Permission rules:
        ADMIN/PEDIDOS: can cancel ANY order at ANY state
        Regular customer: can only cancel PENDIENTE or CONFIRMADO orders
            (once EN_PREP, the kitchen has started — cancellation is blocked)
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
