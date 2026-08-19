"""
WebSocket Manager — singleton room-based connection registry.

Provides a dual-map structure for O(1) lookup:
    - rooms: str|int -> set[WebSocket]  (who is in room X)
    - socket_rooms: WebSocket -> set[str|int]  (which rooms is socket Y in)

Broadcast rules:
    - broadcast(room, payload) sends to all sockets in that room exactly once.
    - broadcast_admin(payload) sends to the 'admin' room only.
    - No-op when the target room is empty.
    - All broadcasts are fire-and-forget; dead sockets are auto-cleaned.

Usage:
    manager = WSManager()
    await manager.connect(websocket, 42)
    await manager.broadcast(42, {"event": "estado_cambiado", ...})
    await manager.broadcast_admin({"event": "estado_cambiado", ...})
    manager.disconnect(websocket)
"""

import logging
from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WSManager:
    """Singleton WebSocket connection manager with dual-map room management."""

    _instance: "WSManager | None" = None

    def __new__(cls) -> "WSManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self.rooms: dict[str | int, set[WebSocket]] = {}
            self.socket_rooms: dict[WebSocket, set[str | int]] = {}

    def connect(self, websocket: WebSocket, room: str | int) -> None:
        """Register an already-accepted WebSocket in both maps.

        The handshake (websocket.accept()) must be performed by the caller
        BEFORE calling this method.

        Args:
            websocket: The Starlette WebSocket connection (already accepted).
            room: Room key — int (pedido_id) or str ('admin').
        """
        # Register in rooms map
        if room not in self.rooms:
            self.rooms[room] = set()
        self.rooms[room].add(websocket)

        # Register in socket_rooms map
        if websocket not in self.socket_rooms:
            self.socket_rooms[websocket] = set()
        self.socket_rooms[websocket].add(room)

        logger.debug(
            "WSManager: socket %s joined room %s (room size: %d, socket rooms: %d)",
            id(websocket), room,
            len(self.rooms.get(room, set())),
            len(self.socket_rooms.get(websocket, set())),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove the socket from ALL rooms and clean both maps.

        Cleans empty rooms from self.rooms after removal.
        Safe to call on already-disconnected sockets (no-op).

        Args:
            websocket: The WebSocket connection to remove.
        """
        rooms = self.socket_rooms.pop(websocket, None)
        if rooms is None:
            logger.debug("WSManager: disconnect called on untracked socket %s", id(websocket))
            return

        for room in rooms:
            room_set = self.rooms.get(room)
            if room_set:
                room_set.discard(websocket)
                if not room_set:
                    del self.rooms[room]
                    logger.debug("WSManager: removed empty room %s", room)

        logger.debug("WSManager: disconnected socket %s from rooms %s", id(websocket), rooms)

    async def broadcast(self, room: str | int, payload: dict) -> None:
        """Send payload to all sockets in the specified room exactly once.

        De-duplication: tracks sent sockets in a set to avoid sending the
        same message twice to a socket that might be in the room set twice
        (should not happen, but defensive).

        No-op if the room has no subscribers.

        Args:
            room: Target room key.
            payload: JSON-serializable dict to send.
        """
        target_sockets = self.rooms.get(room, set())
        if not target_sockets:
            logger.debug("WSManager: broadcast to room %s skipped (no subscribers)", room)
            return

        # Iterate over a snapshot copy; disconnect may mutate self.rooms
        sent: set[WebSocket] = set()
        for ws in list(target_sockets):
            if ws in sent:
                continue
            sent.add(ws)
            await self._send_to(ws, payload)

    async def broadcast_admin(self, payload: dict) -> None:
        """Send payload to all sockets subscribed to the 'admin' room.

        Convenience method that delegates to broadcast('admin', payload).

        Args:
            payload: JSON-serializable dict to send.
        """
        await self.broadcast("admin", payload)

    async def _send_to(self, websocket: WebSocket, payload: dict) -> None:
        """Send a single message to a single WebSocket, catching disconnects.

        If the socket is dead, it is automatically removed from all rooms
        and both maps are cleaned.

        Args:
            websocket: Target WebSocket connection.
            payload: JSON-serializable dict.
        """
        try:
            await websocket.send_json(payload)
        except (WebSocketDisconnect, RuntimeError) as exc:
            logger.debug(
                "WSManager: failed to send to socket %s (%s), cleaning up",
                id(websocket), exc,
            )
            self.disconnect(websocket)

    # ── Debug helpers ───────────────────────────────────────────────────

    @property
    def active_connections(self) -> int:
        """Total number of unique WebSocket connections tracked."""
        return len(self.socket_rooms)

    @property
    def active_rooms(self) -> list[str | int]:
        """List of room keys that currently have subscribers."""
        return list(self.rooms.keys())
