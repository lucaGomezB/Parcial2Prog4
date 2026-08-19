/**
 * WebSocket connection state store (Zustand).
 *
 * Centralises WebSocket connection state so any component can read
 * connectivity status without prop drilling. Follows the same pattern
 * as authStore.
 *
 * State:
 *   - status: 'disconnected' | 'connecting' | 'connected' | 'reconnecting'
 *   - reconnectAttempt: number — current reconnection attempt counter
 *   - maxReconnectAttempts: number — maximum reconnection attempts (default 5)
 *   - lastEvent: WsEvent | null — most recent event received (for debugging)
 *   - connectedAt: number | null — Date.now() when connected
 */
import { create } from "zustand";
import type { WsEvent } from "@/features/pedidos/types/ws";

// ── Types ──

export type WsConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

export interface WsState {
  status: WsConnectionStatus;
  reconnectAttempt: number;
  maxReconnectAttempts: number;
  lastEvent: WsEvent | null;
  connectedAt: number | null;
}

export interface WsActions {
  setStatus: (status: WsConnectionStatus) => void;
  incrementReconnect: () => void;
  resetReconnect: () => void;
  setLastEvent: (event: WsEvent) => void;
}

type WsStore = WsState & WsActions;

// ── Store ──

export const useWsStore = create<WsStore>((set) => ({
  status: 'disconnected',
  reconnectAttempt: 0,
  maxReconnectAttempts: 10,
  lastEvent: null,
  connectedAt: null,

  setStatus: (status) =>
    set({
      status,
      ...(status === 'connected' ? { connectedAt: Date.now() } : {}),
    }),
  incrementReconnect: () =>
    set((state) => ({ reconnectAttempt: state.reconnectAttempt + 1 })),
  resetReconnect: () => set({ reconnectAttempt: 0 }),
  setLastEvent: (event) => set({ lastEvent: event }),
}));

// ── Selectors ──

export const useWsStatus = () => useWsStore((s) => s.status);
export const useWsReconnectAttempt = () => useWsStore((s) => s.reconnectAttempt);
export const useWsLastEvent = () => useWsStore((s) => s.lastEvent);
