/**
 * useAdminPedidoFeed — WebSocket hook for admin real-time order feed.
 *
 * Connects to /ws/admin/pedidos?token=<jwt> and listens for ALL order
 * state change events. On each event, calls the provided onEvent callback
 * and updates the wsStore.
 *
 * Features:
 *   - JWT authentication from authStore
 *   - Only active when user has ADMIN or PEDIDOS role
 *   - Exponential backoff reconnection (same strategy as useEstadoPedidoWS)
 *   - wsStore integration for connection status
 *
 * Usage:
 *   const roles = getUserRoles();
 *   const isGestor = roles.includes("ADMIN") || roles.includes("PEDIDOS");
 *   useAdminPedidoFeed(isGestor, () => loadPedidos());
 */
import { useEffect, useRef, useCallback } from "react";
import { useAuthStore } from "@/shared/store/authStore";
import { useWsStore } from "@/features/pedidos/store/wsStore";
// useNotificationStore import removed — badge now uses useActivePedidosCount hook (backend count).
// If incrementUnseen is re-enabled in the future, re-add this import.
import type { WsEvent } from "@/features/pedidos/types/ws";

const WS_BASE = (import.meta.env.VITE_WS_URL || "ws://localhost:8000") + "/api/v1";

const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000, 30000, 30000];
const MAX_ATTEMPTS = 10;

export function useAdminPedidoFeed(
  enabled: boolean,
  onEvent?: (event: WsEvent) => void,
): void {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const connectingRef = useRef(false);

  // useRef bridge: always points to the latest onEvent callback without
  // triggering reconnects when the inline reference changes on re-render.
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const accessToken = useAuthStore((s) => s.accessToken);
  const setStatus = useWsStore((s) => s.setStatus);
  const setLastEvent = useWsStore((s) => s.setLastEvent);
  const incrementReconnect = useWsStore((s) => s.incrementReconnect);
  const resetReconnect = useWsStore((s) => s.resetReconnect);

  const disconnect = useCallback(() => {
    connectingRef.current = false;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.close(1000, "cleanup");
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!enabled || !accessToken || !mountedRef.current) return;
    if (connectingRef.current) return;

    disconnect();
    connectingRef.current = true;

    const url = `${WS_BASE}/pedidos/ws/admin/pedidos?token=${accessToken}`;
    const socket = new WebSocket(url);
    wsRef.current = socket;

    socket.onopen = () => {
      connectingRef.current = false;
      if (!mountedRef.current) {
        socket.close();
        return;
      }
      attemptRef.current = 0;
      setStatus('connected');
      resetReconnect();
    };

    socket.onmessage = (msg) => {
      try {
        const event: WsEvent = JSON.parse(msg.data as string);
        setLastEvent(event);
        // DISABLED: Badge now uses active pedidos count from backend.
        // useNotificationStore.getState().incrementUnseen();
        onEventRef.current?.(event);
      } catch {
        // Ignore malformed messages
      }
    };

    socket.onclose = () => {
      connectingRef.current = false;
      if (!mountedRef.current) return;
      setStatus('disconnected');

      const attempt = attemptRef.current;
      if (attempt < MAX_ATTEMPTS) {
        const delay = BACKOFF_DELAYS[attempt] || 30000;
        attemptRef.current = attempt + 1;
        incrementReconnect();

        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };

    socket.onerror = () => {
      // onclose will fire after onerror — handle reconnection there
    };
  }, [enabled, accessToken, disconnect, setStatus, setLastEvent, resetReconnect, incrementReconnect]);

  useEffect(() => {
    mountedRef.current = true;

    if (enabled && accessToken) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [connect, disconnect, enabled, accessToken]);
}
