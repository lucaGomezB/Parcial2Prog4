/**
 * useEstadoPedidoWS — WebSocket hook for client-specific order updates.
 *
 * Connects to /ws/pedidos/{pedidoId}?token=<jwt> and listens for real-time
 * state change events. On each event, calls the provided onEvent callback
 * and updates the wsStore.
 *
 * POST-PAGO: Also listens for pago_confirmado events. When received:
 *   1. Clears the cart via useCartStore.clearCarrito()
 *   2. Invalidates pedidos query cache
 *   3. Navigates to the new Pedido page
 *
 * Features:
 *   - JWT authentication from authStore
 *   - Automatic connection lifecycle (connect on mount/enabled, close on unmount)
 *   - Exponential backoff reconnection: 1s, 2s, 4s, 8s, 16s, 30s cap, max 10 attempts
 *   - wsStore integration for connection status
 *
 * Usage:
 *   useEstadoPedidoWS(pedidoId, true, () => loadPedidos());
 */
import { useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/shared/store/authStore";
import { useCartStore } from "@/shared/store/cartStore";
import { useWsStore } from "@/features/pedidos/store/wsStore";
// useNotificationStore import removed — badge now uses useActivePedidosCount hook (backend count).
// If incrementUnseen is re-enabled in the future, re-add this import.
import type { WsEvent } from "@/features/pedidos/types/ws";

const WS_BASE = (import.meta.env.VITE_WS_URL || "ws://localhost:8000") + "/api/v1";

/** Exponential backoff delays in milliseconds (index = attempt number). */
const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000, 30000, 30000];
const MAX_ATTEMPTS = 10;

/** Set of pedido IDs that have been seen via pago_confirmado events. */
const pagosConfirmadosVistos = new Set<number>();

export function useEstadoPedidoWS(
  pedidoId: number,
  enabled: boolean,
  onEvent?: (event: WsEvent) => void,
): void {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const connectingRef = useRef(false);

  // ── Router and query cache for pago_confirmado navigation ──
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;
  const queryClient = useQueryClient();

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

    const url = `${WS_BASE}/pedidos/ws/pedidos/${pedidoId}?token=${accessToken}`;
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

        // ── Handle pago_confirmado: clear cart and navigate ──
        if (event.event === "pago_confirmado" && event.pedido_id) {
          const pid = event.pedido_id;
          if (!pagosConfirmadosVistos.has(pid)) {
            pagosConfirmadosVistos.add(pid);
            useCartStore.getState().clearCarrito();
            // Navigate to the new Pedido detail page
            try {
              navigateRef.current(`/pedidos/${pid}`, { replace: true });
            } catch {
              // Fallback: window.location if navigate fails (hook called outside Router)
              window.location.href = `/pedidos/${pid}`;
            }
            // Invalidate mis-pedidos query cache
            queryClient.invalidateQueries({ queryKey: ['mis-pedidos'] });
          }
        }
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
  }, [enabled, accessToken, pedidoId, disconnect, setStatus, setLastEvent, resetReconnect, incrementReconnect, queryClient]);

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
