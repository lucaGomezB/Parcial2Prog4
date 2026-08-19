/**
 * useStockWebSocket — WebSocket hook for real-time product stock updates.
 *
 * Connects to /api/v1/stock/ws/productos/{productId}?token=<jwt> and listens
 * for stock_actualizado events. On each event, invalidates the TanStack Query
 * cache for the product and updates a local stock state.
 *
 * Features:
 *   - JWT authentication from authStore
 *   - Automatic connection lifecycle (connect on mount/enabled, close on unmount)
 *   - Exponential backoff reconnection: 1s, 2s, 4s, 8s, 16s, 30s cap, max 10 attempts
 *   - Returns { stock, isConnected } for immediate UI use
 *
 * Usage:
 *   const { stock, isConnected } = useStockWebSocket(productId);
 */
import { useEffect, useRef, useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/shared/store/authStore";
import { queryKeys } from "@/shared/api/queryKeys";

const WS_BASE = (import.meta.env.VITE_WS_URL || "ws://localhost:8000") + "/api/v1";

const BACKOFF_DELAYS = [1000, 2000, 4000, 8000, 16000, 30000, 30000, 30000, 30000, 30000];
const MAX_ATTEMPTS = 10;

interface StockEvent {
  event: string;
  entidad_tipo: string;
  entidad_id: number;
  entidad_nombre: string;
  stock_anterior: number;
  stock_nuevo: number;
  motivo: string;
  usuario_id: number | null;
  timestamp: string;
}

interface UseStockWebSocketResult {
  stock: number | null;
  isConnected: boolean;
}

export function useStockWebSocket(productId: number | null): UseStockWebSocketResult {
  const wsRef = useRef<WebSocket | null>(null);
  const attemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const connectingRef = useRef(false);

  const [stock, setStock] = useState<number | null>(null);
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
    if (!productId || !accessToken || !mountedRef.current) return;
    if (connectingRef.current) return;

    disconnect();
    connectingRef.current = true;

    const url = `${WS_BASE}/stock/ws/productos/${productId}?token=${accessToken}`;
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
        const event: StockEvent = JSON.parse(msg.data as string);
        if (event.event === "stock_actualizado" && event.entidad_id === productId) {
          setStock(event.stock_nuevo);
          // Invalidate TanStack Query cache so ProductoDetail re-fetches
          queryClient.invalidateQueries({
            queryKey: queryKeys.productos.detail(productId),
          });
        } else if (event.event === "producto_actualizado" && event.entidad_id === productId) {
          // Invalidate the product detail query so the price updates in real time
          queryClient.invalidateQueries({
            queryKey: queryKeys.productos.detail(productId),
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
  }, [productId, accessToken, disconnect, queryClient]);

  useEffect(() => {
    mountedRef.current = true;

    if (productId && accessToken) {
      connect();
    } else {
      setStock(null);
      setIsConnected(false);
    }

    return () => {
      mountedRef.current = false;
      disconnect();
    };
  }, [connect, disconnect, productId, accessToken]);

  return { stock, isConnected };
}
