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
 * Persistence: Uses Zustand `persist` middleware with sessionStorage so each
 * browser window/tab gets its own isolated session. This enables testing with
 * multiple roles simultaneously (ADMIN in one window, CLIENT in another)
 * without cross-contamination. The httpOnly refresh cookie handles seamless
 * session restoration across browser restarts — the access token does not
 * need to survive restarts.
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { UserInfo } from '@/shared/types/auth'

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
 * Uses Zustand `persist` middleware with sessionStorage.
 * On rehydration, checks token expiry and clears stale sessions.
 * `partialize` excludes transient fields (isLoading, roles — roles is
 * derived from user.roles) from persistence.
 */
export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      // ── Initial state ──
      user: null,
      roles: null,
      accessToken: null,
      expiresAt: null,
      isAuthenticated: false,
      isLoading: false,

      // ── Actions ──

      login: (accessToken, expiresIn, user) => {
        const expiresAt = Date.now() + expiresIn * 1000
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
        // Clear persisted storage explicitly so sessionStorage is wiped
        useAuthStore.persist.clearStorage()
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
        set({
          accessToken,
          expiresAt,
        })
      },

      setUser: (user) => {
        set({
          user,
          roles: user.roles,
          isAuthenticated: true,
        })
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => sessionStorage),
      // Only persist the token fields. user and isAuthenticated are derived
      // on bootstrap via /auth/me — persisting them is redundant and bloats storage.
      partialize: (state) => ({
        accessToken: state.accessToken,
        expiresAt: state.expiresAt,
      }),
      onRehydrateStorage: () => {
        return (state, error) => {
          if (error) {
            console.error('[authStore] rehydration error:', error)
            return
          }
          if (!state) return
          // Validate persisted session: token must exist and not be expired
          const isValid = state.accessToken && state.expiresAt && Date.now() < state.expiresAt
          if (!isValid) {
            useAuthStore.persist.clearStorage()
            useAuthStore.setState({
              user: null,
              roles: null,
              accessToken: null,
              expiresAt: null,
              isAuthenticated: false,
              isLoading: false,
            })
          }
        }
      },
    }
  )
)

// ── Selectors ──

export const useAuthUser = () => useAuthStore((s) => s.user)
export const useAuthRoles = () => useAuthStore((s) => s.roles)
export const useIsAuthenticated = () => useAuthStore((s) => s.isAuthenticated)
export const useIsLoading = () => useAuthStore((s) => s.isLoading)
