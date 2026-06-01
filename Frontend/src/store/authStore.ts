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
 * Security note: ALL state is kept in memory ONLY. Nothing is persisted to
 * localStorage or sessionStorage. On page reload the store resets to initial
 * values, and refreshSession() in client.ts restores the session via the
 * httpOnly refresh cookie. This design prevents XSS-based token theft.
 */
import { create } from 'zustand'
import type { UserInfo } from '../api/client'

// ── Types ──

/**
 * roles = null   → undetermined / needs login
 * roles = []     → guest (browsing without a token)
 * roles = [...]  → authenticated with those roles
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
 * Initial state: everything at null or false. On page reload, the store
 * starts empty. The bootstrap effect in App.tsx calls refreshSession()
 * to restore the session from the httpOnly cookie if one exists.
 *
 * Why in-memory instead of localStorage?
 *   The JWT access token is sensitive. Storing it in localStorage makes it
 *   accessible to any JavaScript running on the same origin, which means an
 *   XSS vulnerability could leak it. Keeping it in memory means it is lost
 *   on page reload (which triggers a fresh refreshSession() call via the
 *   httpOnly cookie, which the attacker cannot read).
 */
export const useAuthStore = create<AuthStore>((set) => ({
  // ── Initial state ──
  user: null,
  roles: null,
  accessToken: null,
  expiresAt: null,
  isAuthenticated: false,
  isLoading: false,

  // ── Actions ──

  /**
   * Called after a successful login. Stores the JWT (with computed expiry
   * timestamp in milliseconds), the user profile, and marks the session
   * as authenticated.
   *
   * expiresAt = Date.now() + expiresIn * 1000
   *   (the backend sends expiresIn in seconds; we convert to ms for comparison).
   */
  login: (accessToken, expiresIn, user) => set({
    accessToken,
    expiresAt: Date.now() + expiresIn * 1000,
    user,
    roles: user.roles,
    isAuthenticated: true,
    isLoading: false,
  }),

  /**
   * Resets everything to the initial (unauthenticated) state.
   * Should also trigger a POST to /auth/logout on the backend to
   * invalidate the httpOnly refresh cookie server-side.
   */
  logout: () => set({
    user: null,
    roles: null,
    accessToken: null,
    expiresAt: null,
    isAuthenticated: false,
    isLoading: false,
  }),

  /** Updates only the roles array. Useful when roles change mid-session. */
  setRoles: (roles) => set({ roles }),

  /** Controls the loading flag for the initial session verification spinner. */
  setLoading: (loading) => set({ isLoading: loading }),

  /**
   * Updates the access token and its expiry without touching user data.
   * Used by the refresh interceptor after a successful token renewal.
   */
  setSession: (accessToken, expiresIn) => set({
    accessToken,
    expiresAt: Date.now() + expiresIn * 1000,
  }),

  /**
   * Sets the full user profile and marks the session as authenticated.
   * Roles are extracted from the user object automatically.
   */
  setUser: (user) => set({
    user,
    roles: user.roles,
    isAuthenticated: true,
  }),
}))

// ── Selectors ──

/**
 * Pre-defined selectors for fine-grained reactivity.
 *
 * Each selector extracts a single slice of the store so that a component
 * only re-renders when its specific slice changes, not when any part of
 * the store changes.
 *
 * Usage:
 *   const user = useAuthUser()            // re-renders only when user changes
 *   const roles = useAuthRoles()          // re-renders only when roles change
 *   const authed = useIsAuthenticated()   // re-renders only on login/logout
 *   const loading = useIsLoading()        // re-renders only when loading toggles
 */
export const useAuthUser = () => useAuthStore((s) => s.user)
export const useAuthRoles = () => useAuthStore((s) => s.roles)
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated)
export const useIsLoading = () => useAuthStore((s) => s.isLoading)
