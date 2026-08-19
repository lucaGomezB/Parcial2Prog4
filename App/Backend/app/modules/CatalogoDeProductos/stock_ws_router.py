"""
Stock WebSocket endpoints — real-time product stock visibility.

Provides two WebSocket routes:
    GET /api/v1/stock/ws/productos/{id}  → subscribes to room producto_{id}
    GET /api/v1/stock/ws/admin/productos → subscribes to room stock_admin

Authentication: JWT query parameter ?token=<jwt>.
Reuses the singleton WSManager from core.dependencies.
"""
import logging
from fastapi import APIRouter, Depends, WebSocket, WebSocketException
from sqlmodel import Session
from app.core.database import get_session
from app.core.dependencies import get_ws_manager
from app.core.websocket_manager import WSManager
from app.core.security import decode_token

logger = logging.getLogger(__name__)

stock_ws_router = APIRouter(tags=["stock-websocket"])


async def _get_user_from_ws_token(
    websocket: WebSocket,
    session: Session,
):
    """Extract and validate JWT from WS query params. Reused from Pedido router."""
    token = websocket.query_params.get("token")
    if not token:
        logger.warning("Stock WS auth: missing token")
        raise WebSocketException(code=4001, reason="Token requerido")

    token_data = decode_token(token)
    if not token_data:
        logger.warning("Stock WS auth: invalid or expired token")
        raise WebSocketException(code=4001, reason="Token invalido o expirado")

    from app.modules.IdentidadYAcceso.uow import IdentidadYAccesoUnitOfWork
    user = IdentidadYAccesoUnitOfWork(session).usuarios.get_with_roles(token_data.user_id)
    if not user:
        logger.warning("Stock WS auth: user %s not found", token_data.user_id)
        raise WebSocketException(code=4001, reason="Usuario no encontrado")

    return user


@stock_ws_router.websocket("/ws/productos/{producto_id}")
async def ws_producto(
    websocket: WebSocket,
    producto_id: int,
    session: Session = Depends(get_session),
    ws_manager: WSManager = Depends(get_ws_manager),
):
    """WebSocket for client-specific product stock updates.

    Any authenticated user can subscribe to a specific product's stock room.
    Room key: producto_{producto_id}
    """
    await websocket.accept()

    try:
        user = await _get_user_from_ws_token(websocket, session)
    except WebSocketException:
        await websocket.close(code=4001, reason="Token requerido")
        return

    room = f"producto_{producto_id}"
    ws_manager.connect(websocket, room)
    logger.debug("Stock WS: user %s joined room %s", user.id, room)

    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket)


@stock_ws_router.websocket("/ws/admin/productos")
async def ws_admin_productos(
    websocket: WebSocket,
    session: Session = Depends(get_session),
    ws_manager: WSManager = Depends(get_ws_manager),
):
    """WebSocket for admin real-time stock feed.

    Restricted to ADMIN and STOCK roles.
    Room key: stock_admin
    """
    await websocket.accept()

    try:
        user = await _get_user_from_ws_token(websocket, session)
    except WebSocketException:
        await websocket.close(code=4001, reason="Token requerido")
        return

    user_roles = [rol.codigo for rol in user.roles]
    if "ADMIN" not in user_roles and "STOCK" not in user_roles:
        await websocket.close(code=4003, reason="No autorizado")
        return

    ws_manager.connect(websocket, "stock_admin")
    logger.debug("Stock WS: admin user %s joined stock_admin room", user.id)

    try:
        while True:
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket)


# ── Broadcast helper for derived stock propagation ──────────────────────
# Used by IngredienteService.actualizar_stock() and PedidoService to push
# updated derived stock values to WebSocket clients when ingredient stock
# changes affect product availability.


def broadcast_derived_stock_for_products(
    session: Session,
    producto_ids: list[int],
    ws_manager,
    motivo: str = "ingrediente_actualizado",
):
    """Recompute derived stock for given products and broadcast via WebSocket.

    Only broadcasts for non-es_producto_terminado products (they use
    stock_manual, not ingredient-derived stock). Broadcasts to both
    the product-specific room (producto_{id}) and the admin feed (stock_admin).

    IMPORTANT: This function does NOT call session.commit(). The caller's
    Unit of Work owns the transaction boundary. All `session.add()`
    calls for stock_cantidad updates are committed by the caller's UoW.

    Args:
        session: SQLModel session (open, inside caller's UoW).
        producto_ids: List of product IDs whose derived stock may have changed.
        ws_manager: WSManager instance (None to skip broadcast).
        motivo: Reason string for the stock_actualizado event payload.
    """
    if not producto_ids or ws_manager is None:
        return

    from datetime import datetime, timezone
    from sqlmodel import select as sm_select

    from app.core.dependencies import fire_broadcast
    from app.modules.CatalogoDeProductos.Producto.models import Producto
    from .Producto.repository import ProductoRepository

    # Only compute derived stock for active, non-terminado products
    products = session.exec(
        sm_select(Producto).where(
            Producto.id.in_(producto_ids),
            Producto.es_producto_terminado == False,
            Producto.deleted_at.is_(None),
        )
    ).all()

    if not products:
        return

    repo = ProductoRepository(session)
    stock_map = repo.compute_derived_stock_batch([p.id for p in products])

    for producto in products:
        nuevo_stock = stock_map.get(producto.id, 0)

        # Persist derived stock to the column so producto.stock_cantidad stays in sync
        producto.stock_cantidad = nuevo_stock
        session.add(producto)

        payload = {
            "event": "stock_actualizado",
            "entidad_tipo": "producto",
            "entidad_id": producto.id,
            "entidad_nombre": producto.nombre,
            "stock_anterior": None,  # derived stock does not track "previous"
            "stock_nuevo": nuevo_stock,
            "motivo": motivo,
            "usuario_id": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        fire_broadcast(ws_manager, f"producto_{producto.id}", payload)
        fire_broadcast(ws_manager, "stock_admin", payload)

    # NOTE: session.commit() intentionally removed — the caller's UoW owns the commit.


def broadcast_price_update_for_products(
    session: Session,
    producto_ids: list[int],
    ws_manager,
    motivo: str = "ingrediente_precio_actualizado",
    usuario_id: int | None = None,
):
    """Broadcast producto_actualizado events for products affected by ingredient price changes.

    Queries active non-terminado products by ID, computes price deltas, and broadcasts
    a producto_actualizado event to the product-specific room (producto_{id}) and the
    admin feed (stock_admin).

    IMPORTANT: This function does NOT call session.commit(). The caller's
    Unit of Work owns the transaction boundary. All recalculations happen
    before this broadcast, so this function only queries and broadcasts.

    Args:
        session: SQLModel session (open, inside caller's UoW).
        producto_ids: List of product IDs whose prices may have changed.
        ws_manager: WSManager instance (None to skip broadcast).
        motivo: Reason string for the producto_actualizado event payload.
        usuario_id: User ID for audit (None for system-triggered events).
    """
    if not producto_ids or ws_manager is None:
        return

    try:
        from datetime import datetime, timezone
        from sqlmodel import select as sm_select

        from app.core.dependencies import fire_broadcast
        from app.modules.CatalogoDeProductos.Producto.models import Producto

        # Only broadcast for active, non-terminado products
        products = session.exec(
            sm_select(Producto).where(
                Producto.id.in_(producto_ids),
                Producto.es_producto_terminado == False,
                Producto.deleted_at.is_(None),
            )
        ).all()

        if not products:
            return

        now_iso = datetime.now(timezone.utc).isoformat()

        for producto in products:
            payload = {
                "event": "producto_actualizado",
                "entidad_tipo": "producto",
                "entidad_id": producto.id,
                "entidad_nombre": producto.nombre,
                "precio_anterior": None,  # no previous tracking — prices overwritten in-place
                "precio_nuevo": float(producto.precio_actual),
                "precio_base": float(producto.precio_base),
                "motivo": motivo,
                "usuario_id": usuario_id,
                "timestamp": now_iso,
            }
            fire_broadcast(ws_manager, f"producto_{producto.id}", payload)
            fire_broadcast(ws_manager, "stock_admin", payload)
    except Exception:
        logger.exception(
            "Failed to broadcast price update for products %s (motivo=%s)",
            producto_ids, motivo,
        )
