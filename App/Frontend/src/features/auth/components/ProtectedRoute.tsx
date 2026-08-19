/**
 * ProtectedRoute — Auth-guard wrapper component.
 *
 * Checks authentication state and optionally enforces role-based access.
 * If not authenticated, redirects to /login. If allowedRoles is provided
 * and the user lacks any matching role, redirects to /.
 *
 * Does NOT replace the three-state role gate in App.tsx (null = booting).
 * Used for post-bootstrap route guarding.
 */
import { type ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/shared/store/authStore'

export interface ProtectedRouteProps {
  children: ReactNode
  allowedRoles?: string[]
}

export function ProtectedRoute({ children, allowedRoles }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const userRoles = user?.roles ?? []
    const hasPermission = allowedRoles.some((r) => userRoles.includes(r))
    if (!hasPermission) {
      return <Navigate to="/" replace />
    }
  }

  return <>{children}</>
}
