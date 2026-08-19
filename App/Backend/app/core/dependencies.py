"""
Core dependency injection module.

Provides singleton-style dependencies for the FastAPI application
and reusable role-authorization constants plus pagination dependency.
"""

import asyncio
import logging
from fastapi import Query
from app.core.websocket_manager import WSManager

logger = logging.getLogger(__name__)

# ── Role constant aliases ──────────────────────────────────────────────
# Reusable role-list constants for require_roles() dependency calls.
# Usage: dependencies=[Depends(require_roles(AdminOnly))]

AdminOnly = ["ADMIN"]
AdminOrStock = ["ADMIN", "STOCK"]
AdminOrPedidos = ["ADMIN", "PEDIDOS"]
AdminOrStockOrPedidos = ["ADMIN", "STOCK", "PEDIDOS"]

# ── Singleton WSManager instance ──
_ws_manager: WSManager | None = None


def get_ws_manager() -> WSManager:
    """Return the singleton WSManager instance, creating it on first call.

    Suitable for use as a FastAPI dependency:
        ws_manager: WSManager = Depends(get_ws_manager)
    """
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WSManager()
        logger.info("WSManager singleton initialized")
    return _ws_manager


def fire_broadcast(ws_manager: WSManager | None, room: str | int, payload: dict) -> None:
    """Fire-and-forget broadcast to a specific room from a sync context.

    Uses asyncio.run() to execute the async broadcast. Safe to call from
    thread-pool threads (sync FastAPI route handlers) because those threads
    do not have a running event loop.

    Args:
        ws_manager: The WSManager instance (or None to skip).
        room: Target room key.
        payload: JSON-serializable dict.
    """
    if ws_manager is None:
        return
    try:
        asyncio.run(ws_manager.broadcast(room, payload))
    except Exception as exc:
        logger.warning("WS broadcast to room %s failed: %s", room, exc)


def fire_broadcast_admin(ws_manager: WSManager | None, payload: dict) -> None:
    """Fire-and-forget broadcast to the admin room from a sync context.

    Args:
        ws_manager: The WSManager instance (or None to skip).
        payload: JSON-serializable dict.
    """
    if ws_manager is None:
        return
    try:
        asyncio.run(ws_manager.broadcast_admin(payload))
    except Exception as exc:
        logger.warning("WS admin broadcast failed: %s", exc)


def fire_broadcast_user(ws_manager: WSManager | None, user_id: int, payload: dict) -> None:
    """Fire-and-forget broadcast to a user-specific room from a sync context.

    The room key is f"user_{user_id}". Clients connect to this room via
    the /ws/cliente/pedidos endpoint to receive real-time updates for all
    their orders with a single WebSocket connection.

    Args:
        ws_manager: The WSManager instance (or None to skip).
        user_id: The user ID whose client room should receive the broadcast.
        payload: JSON-serializable dict.
    """
    if ws_manager is None:
        return
    try:
        asyncio.run(ws_manager.broadcast(f"user_{user_id}", payload))
    except Exception as exc:
        logger.warning("WS user broadcast to user_%s failed: %s", user_id, exc)


async def PaginationDep(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Max records to return (1-100)"),
) -> dict:
    """FastAPI dependency that provides validated skip/limit pagination.

    Usage in endpoint signatures:
        pagination: dict = Depends(PaginationDep)
        skip = pagination["skip"]
        limit = pagination["limit"]
    """
    return {"skip": skip, "limit": limit}
