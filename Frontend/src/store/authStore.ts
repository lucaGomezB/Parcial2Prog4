/**
 * Authentication state store (Zustand).
 *
 * Centralises all session-related data in a single global store so that any
 * component can read authentication state without prop drilling.
 *
 * Zustand primer:
 *   - create((set) => ({...}))  → defines the store
 *   - useAuthStore()            → reactive hook (component re-renders on change)
 *   - useAuthStore.getState()   → synchronous read (outside React components)
 *   - set({...})                → partial merge (no manual spread needed)
 *
 * Three-state role pattern:
 *   roles = null  → not yet determined (initial/app-boot state)
 *   roles = []    → guest (no token, browsing publicly)
 *   roles = [...] → authenticated with roles, e.g. ["ADMIN", "CLIENTE"]
 *
 * Persistence: The store saves accessToken + user to localStorage so the
 * session survives page reloads. On init, it hydrates from localStorage.
 */
import { create } from 'zustand'
import type { UserInfo } from '../api/client'

// ── localStorage keys ──
const LS_ACCESS_TOKEN = 'auth_accessToken'
const LS_EXPIRES_AT = 'auth_expiresAt'
const LS_USER = 'auth_user'

/** Reads a value from localStorage, returning null on error/missing. */
function lsRead<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key)
    if (raw === null) return null
    return JSON.parse(raw) as T
  } catch {
    return null
  }
}

/** Writes a value to localStorage (null = remove). */
function lsWrite<T>(key: string, value: T | null): void {
  try {
    if (value === null) {
      localStorage.removeItem(key)
    } else {
      localStorage.setItem(key, JSON.stringify(value))
    }
  } catch {
    // localStorage might be full or blocked — silently ignore
  }
}

/** Hydrate initial state from localStorage. */
function hydrateFromLS() {
  const accessToken = lsRead<string>(LS_ACCESS_TOKEN)
  const expiresAt = lsRead<number>(LS_EXPIRES_AT)
  const user = lsRead<UserInfo>(LS_USER)
  const isAuthenticated = !!(accessToken && user)

  // If token expired, clear everything
  if (isAuthenticated && expiresAt && Date.now() > expiresAt) {
    lsWrite(LS_ACCESS_TOKEN, null)
    lsWrite(LS_EXPIRES_AT, null)
    lsWrite(LS_USER, null)
    return {
      user: null,
      roles: null,
      accessToken: null,
      expiresAt: null,
      isAuthenticated: false,
      isLoading: false,
    }
  }

  return {
    user,
    roles: user?.roles ?? null,
    accessToken,
    expiresAt,
    isAuthenticated,
    isLoading: false,
  }
}

// ── Types ──

export interface AuthState {
  user: UserInfo | null
  roles: string[] | null
  accessToken: string | null
  expiresAt: number | null
  isAuthenticated: boolean
  isLoading: boolean
}

export interface AuthActions {
  /** Full login: stores the JWT, computes expiry, and saves user data. */
  login: (accessToken: string, expiresIn: number, user: UserInfo) => void
  /** Clears all auth state (token, user, roles) back to null/false. */
  logout: () => void
  /** Updates only the roles array without touching other fields. */
  setRoles: (roles: string[]) => void
  /** Toggles the loading spinner state. */
  setLoading: (loading: boolean) => void
  /**
   * Updates access token and its expiry only.
   * Used by refreshSession() when the token is renewed but user data
   * remains unchanged.
   */
  setSession: (accessToken: string, expiresIn: number) => void
  /**
   * Stores the full user object (including roles) and marks the session
   * as authenticated. Called after a successful /auth/me response.
   */
  setUser: (user: UserInfo) => void
}

type AuthStore = AuthState & AuthActions

/**
 * Store definition.
 *
 * Hydrates from localStorage on creation so the session survives page reloads.
 * Every state change syncs back to localStorage automatically.
 */
export const useAuthStore = create<AuthStore>((set) => ({
  // ── Initial state (hydrated from localStorage) ──
  ...hydrateFromLS(),

  // ── Actions ──

  login: (accessToken, expiresIn, user) => {
    const expiresAt = Date.now() + expiresIn * 1000
    // Persist to localStorage
    lsWrite(LS_ACCESS_TOKEN, accessToken)
    lsWrite(LS_EXPIRES_AT, expiresAt)
    lsWrite(LS_USER, user)

    set({
      accessToken,
      expiresAt,
      user,
      roles: user.roles,
      isAuthenticated: true,
      isLoading: false,
    })
  },

  logout: () => {
    // Clear localStorage
    lsWrite(LS_ACCESS_TOKEN, null)
    lsWrite(LS_EXPIRES_AT, null)
    lsWrite(LS_USER, null)

    set({
      user: null,
      roles: null,
      accessToken: null,
      expiresAt: null,
      isAuthenticated: false,
      isLoading: false,
    })
  },

  setRoles: (roles) => set({ roles }),

  setLoading: (loading) => set({ isLoading: loading }),

  setSession: (accessToken, expiresIn) => {
    const expiresAt = Date.now() + expiresIn * 1000
    // Persist to localStorage
    lsWrite(LS_ACCESS_TOKEN, accessToken)
    lsWrite(LS_EXPIRES_AT, expiresAt)

    set({
      accessToken,
      expiresAt,
    })
  },

  setUser: (user) => {
    // Persist to localStorage
    lsWrite(LS_USER, user)

    set({
      user,
      roles: user.roles,
      isAuthenticated: true,
    })
  },
}))

// ── Selectors ──

export const useAuthUser = () => useAuthStore((s) => s.user)
export const useAuthRoles = () => useAuthStore((s) => s.roles)
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated)
export const useIsLoading = () => useAuthStore((s) => s.isLoading)
