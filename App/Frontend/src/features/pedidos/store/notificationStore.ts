/**
 * Lightweight Zustand store for tracking unseen pedido-state-change notifications.
 *
 * Used by the WebSocket layer to increment a counter when a pedido changes estado
 * and by the topbar notification bell to display the badge count and reset it
 * when the user opens the notifications panel.
 */
import { create } from "zustand";

/** Shape of the notification count state exposed to UI components. */
export interface NotificationState {
  unseenCount: number;
  incrementUnseen: () => void;
  resetUnseen: () => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  unseenCount: 0,
  incrementUnseen: () => set((state) => ({ unseenCount: state.unseenCount + 1 })),
  resetUnseen: () => set({ unseenCount: 0 }),
}));
