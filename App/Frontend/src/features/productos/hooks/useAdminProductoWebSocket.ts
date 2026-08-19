/**
 * useAdminProductoWebSocket — WebSocket hook for the admin product feed.
 *
 * Connects to /api/v1/stock/ws/admin/productos?token=<jwt> and listens for
 * producto_actualizado events broadcast to the stock_admin room.
 * On each event, invalidates the TanStack Query cache for the full product
 * list so the admin CRUD table re-fetches updated prices.
 *
 * Features:
 *   - JWT authentication from authStore
 *   - Automatic connection lifecycle (connect on mount/enabled, close on unmount)
 *   - Exponential backoff reconnection: 1s, 2s, 4s, 8s, 16s, 30s cap, max 10 attempts
 *   - Returns { isConnected } for connection status display
 *   - Disabled when enabled=false (role gate)
 *
 * Usage:
 *   const { isConnected } = useAdminProductoWebSocket({ enabled: isAdminOrStock });
 */
import { useEffect, useRef, useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/shared/store/authStore";
import { queryKeys } from "@/shared/api/queryKeys";

const WS_BASE = (import.meta.env.VITE_WS_URL || "ws://localhost:8000") + "/api/v1";

const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000, 30000, 30000];
const MAX_ATTEMPTS = 10;

interface PriceEvent {
  event: string;
  entidad_tipo: string;
  entidad_id: number;
  entidad_nombre: string;
  precio_anterior: number | null;
  precio_nuevo: number;
  precio_base: number;
  motivo: string;
  usuario_id: number | null;
  timestamp: string;
}

interface UseAdminProductoWebSocketOptions {
  enabled: boolean;
}

interface UseAdminProductoWebSocketResult {
  isConnected: boolean;
}

export function useAdminProductoWebSocket(
  { enabled }: UseAdminProductoWebSocketOptions = { enabled: false }
): UseAdminProductoWebSocketResult {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const connectingRef = useRef(false);

  const [isConnected, setIsConnected] = useState(false);

  const accessToken = useAuthStore((s) => s.accessToken);
  const queryClient = useQueryClient();

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
    setIsConnected(false);
  }, []);

  const connect = useCallback(() => {
    if (!enabled || !accessToken || !mountedRef.current) return;
    if (connectingRef.current) return;

    disconnect();
    connectingRef.current = true;

    const url = `${WS_BASE}/stock/ws/admin/productos?token=${accessToken}`;
    const socket = new WebSocket(url);
    wsRef.current = socket;

    socket.onopen = () => {
      connectingRef.current = false;
      if (!mountedRef.current) {
        socket.close();
        return;
      }
      attemptRef.current = 0;
      setIsConnected(true);
    };

    socket.onmessage = (msg) => {
      try {
        const event: PriceEvent = JSON.parse(msg.data as string);
        if (event.event === "producto_actualizado") {
          // Invalidate the full product list so admin table re-fetches
          queryClient.invalidateQueries({
            queryKey: queryKeys.productos.all,
          });
        }
      } catch {
        // Ignore malformed messages
      }
    };

    socket.onclose = () => {
      connectingRef.current = false;
      if (!mountedRef.current) return;
      setIsConnected(false);

      const attempt = attemptRef.current;
      if (attempt < MAX_ATTEMPTS) {
        const delay = BACKOFF_DELAYS[attempt] || 30000;
        attemptRef.current = attempt + 1;

        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };

    socket.onerror = () => {
      // onclose will fire after onerror — handle reconnection there
    };
  }, [enabled, accessToken, disconnect, queryClient]);

  useEffect(() => {
    mountedRef.current = true;

    if (enabled && accessToken) {
      connect();
    } else {
      setIsConnected(false);
    }

    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [connect, disconnect, enabled, accessToken]);

  return { isConnected };
}
