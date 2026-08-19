/**
 * UI state store (Zustand) — ephemeral UI state.
 *
 * Manages layout toggles and loading state that are global to the app shell.
 * This state is NOT persisted — it resets on every page reload.
 *
 * State:
 *   - sidebarOpen: boolean — desktop sidebar toggle
 *   - mobileMenuOpen: boolean — mobile hamburger menu toggle
 *   - loading: boolean — global loading overlay state
 */
import { create } from 'zustand'

// ── Types ──

export interface UiState {
  sidebarOpen: boolean
  mobileMenuOpen: boolean
  loading: boolean
}

export interface UiActions {
  toggleSidebar: () => void
  setMobileMenuOpen: (open: boolean) => void
  setLoading: (loading: boolean) => void
}

type UiStore = UiState & UiActions

// ── Store ──

export const useUiStore = create<UiStore>((set) => ({
  sidebarOpen: true,
  mobileMenuOpen: false,
  loading: false,

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),
  setLoading: (loading) => set({ loading }),
}))

// ── Selectors ──

export const useSidebarOpen = () => useUiStore((s) => s.sidebarOpen)
export const useMobileMenuOpen = () => useUiStore((s) => s.mobileMenuOpen)
export const useIsLoading = () => useUiStore((s) => s.loading)
