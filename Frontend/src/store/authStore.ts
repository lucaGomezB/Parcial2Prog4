import { create } from 'zustand'
import type { UserInfo } from '../api/client'

// ── Types ──

/**
 * roles = null   → no determinado / necesita login
 * roles = []     → invitado (sin token, browsing)
 * roles = [...]  → autenticado con esos roles
 */
export interface AuthState {
  user: UserInfo | null
  roles: string[] | null
  accessToken: string | null
  expiresAt: number | null
  isAuthenticated: boolean
  isLoading: boolean
}

export interface AuthActions {
  login: (accessToken: string, expiresIn: number, user: UserInfo) => void
  logout: () => void
  setRoles: (roles: string[]) => void
  setLoading: (loading: boolean) => void
  setSession: (accessToken: string, expiresIn: number) => void
  setUser: (user: UserInfo) => void
}

type AuthStore = AuthState & AuthActions

// ── Store (TODO en memoria — nada en localStorage) ──

export const useAuthStore = create<AuthStore>((set) => ({
  // ── Estado inicial: vacío ──
  user: null,
  roles: null,
  accessToken: null,
  expiresAt: null,
  isAuthenticated: false,
  isLoading: false,

  // ── Actions ──
  login: (accessToken, expiresIn, user) => set({
    accessToken,
    expiresAt: Date.now() + expiresIn * 1000,
    user,
    roles: user.roles,
    isAuthenticated: true,
    isLoading: false,
  }),

  logout: () => set({
    user: null,
    roles: null,
    accessToken: null,
    expiresAt: null,
    isAuthenticated: false,
    isLoading: false,
  }),

  setRoles: (roles) => set({ roles }),

  setLoading: (loading) => set({ isLoading: loading }),

  setSession: (accessToken, expiresIn) => set({
    accessToken,
    expiresAt: Date.now() + expiresIn * 1000,
  }),

  setUser: (user) => set({
    user,
    roles: user.roles,
    isAuthenticated: true,
  }),
}))

// ── Selectores ──

export const useAuthUser = () => useAuthStore((s) => s.user)
export const useAuthRoles = () => useAuthStore((s) => s.roles)
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated)
export const useIsLoading = () => useAuthStore((s) => s.isLoading)
