/**
 * App — Thin application shell.
 *
 * Responsibilities:
 *  - Bootstrap session verification on mount (httpOnly refresh cookie).
 *  - Derive role flags (isGuest, isClient, isAdmin, etc.).
 *  - Build navigation items based on role.
 *  - Render layout: nav bar (responsive with hamburger on mobile) + main content + session timeout modal.
 *  - WS connection indicator in navbar.
 *
 * Route definitions live in router.tsx. App.tsx contains NO inline route definitions.
 */
import { NavLink, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { AppRoutes, UnauthenticatedRoutes } from './router'
import SessionTimeoutModal from '@/features/auth/components/SessionTimeoutModal'
import ToastContainer from '@/shared/components/Toast'
import { apiFetch, getAccessToken, refreshSession } from '@/shared/api/client'
import type { UserInfo } from '@/shared/types/auth'
import { useCartStore } from '@/shared/store/cartStore'
import { useAuthStore } from '@/shared/store/authStore'
import { useUiStore } from '@/shared/store/uiStore'
import { NotificationBadge } from '@/features/pedidos/components/NotificationBadge'

/* ── Helpers ── */

function hasRole(roles: string[], ...allowed: string[]) {
  return allowed.some((r) => roles.includes(r));
}

function App() {
  const [verifying, setVerifying] = useState(true)
  const roles = useAuthStore((s) => s.roles)
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()
  const cartCount = useCartStore((s) => s.getItemCount())
  const mobileMenuOpen = useUiStore((s) => s.mobileMenuOpen)
  const setMobileMenuOpen = useUiStore((s) => s.setMobileMenuOpen)

  useEffect(() => {
    async function bootstrap() {
      useCartStore.getState().hydrate();

      const { accessToken, expiresAt } = useAuthStore.getState()
      const hadToken = !!accessToken

      if (accessToken && expiresAt && Date.now() < expiresAt) {
        try {
          const user = await apiFetch<UserInfo>('/auth/me')
          useAuthStore.getState().setUser(user)
          useCartStore.getState().hydrate();
          setVerifying(false)
          return
        } catch {
          // Token invalid — fall through to try refresh or logout
        }
      }

      // Only restore session via refresh cookie if this window already had a token.
      // Prevents fresh private windows from auto-logging in as a user from another window.
      if (hadToken) {
        const hasSession = await refreshSession()

        if (!hasSession) {
          useAuthStore.getState().logout()
          useCartStore.getState().hydrate();
          setVerifying(false)
          return
        }

        try {
          const user = await apiFetch<UserInfo>('/auth/me')
          useAuthStore.getState().setUser(user)
          useCartStore.getState().hydrate();
        } catch {
          useCartStore.getState().hydrate();
        }
      } else {
        useAuthStore.getState().logout()
        useCartStore.getState().clearCarrito();
      }
      setVerifying(false)
    }

    bootstrap()
  }, [])

  const handleLogout = async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } catch {
      // If the server call fails, still clear local state.
    }
    useAuthStore.getState().logout()
    useCartStore.getState().clearCarrito()
    navigate('/login')
  }

  // ── Loading state ──
  if (verifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <p className="text-gray-500">Verificando sesion...</p>
      </div>
    )
  }

  // ── Unauthenticated state ──
  if (roles === null) {
    return (
      <UnauthenticatedRoutes />
    )
  }

  // ── Role-based flags ──
  const isGuest = !getAccessToken();
  const isClient = !isGuest && !hasRole(roles, 'ADMIN', 'STOCK', 'PEDIDOS')
  const isAdmin = hasRole(roles, 'ADMIN')
  const isStock = hasRole(roles, 'STOCK')
  const isPedidos = hasRole(roles, 'PEDIDOS')

  // ── Navigation items ──
  let navItems: { to: string; label: string }[];
  if (isGuest) {
    navItems = [{ to: '/productos', label: 'Menu' }];
  } else if (isClient) {
    navItems = [
      { to: '/productos', label: 'Menu' },
      { to: '/pedidos', label: 'Mis Pedidos' },
      { to: '/direcciones', label: 'Mis direcciones de Entrega' },
      { to: '/carrito', label: `Carrito${cartCount > 0 ? ` (${cartCount})` : ''}` },
    ];
  } else if (isStock) {
    navItems = [{ to: '/productos', label: 'Productos' }];
  } else if (isPedidos) {
    navItems = [{ to: '/pedidos', label: 'Pedidos' }];
  } else if (isAdmin) {
    navItems = [
      { to: '/categorias', label: 'Categorias' },
      { to: '/ingredientes', label: 'Ingredientes' },
      { to: '/productos', label: 'Productos' },
      { to: '/pedidos', label: 'Pedidos' },
      { to: '/direcciones', label: 'Locales' },
    ];
    navItems.splice(0, 0, { to: '/admin/dashboard', label: 'Dashboard' });
    navItems.splice(1, 0, { to: '/admin/usuarios', label: 'Usuarios' });
    navItems.splice(2, 0, { to: '/admin/formas-pago', label: 'Medios de Pago' });
    navItems.splice(3, 0, { to: '/admin/unidades-medida', label: 'Unidades de Medida' });
  } else {
    navItems = [
      { to: '/productos', label: 'Productos' },
      { to: '/pedidos', label: 'Pedidos' },
      { to: '/direcciones', label: 'Direcciones' },
      { to: '/carrito', label: `Carrito${cartCount > 0 ? ` (${cartCount})` : ''}` },
    ];
  }

  return (
    <div className="min-h-screen bg-white">
        {/* ── Navbar (responsive) ── */}
        <nav className="bg-gray-800 text-white px-4 py-3">
          <div className="flex justify-between items-center">
            {/* Left: brand + desktop nav links */}
            <div className="flex items-center gap-4">
              <span className="font-bold mr-2">{isClient || isGuest ? '' : 'Catalogo de Productos'}</span>

              {/* Desktop nav links (hidden on mobile) */}
              <div className="hidden md:flex gap-2">
                {navItems.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `px-3 py-1 rounded ${isActive ? 'bg-gray-600' : 'hover:bg-gray-700'}`
                    }
                  >
                    {item.label}
                    {item.to === '/pedidos' && <NotificationBadge />}
                  </NavLink>
                ))}
              </div>
            </div>

            {/* Right: user info + logout + hamburger */}
            <div className="flex items-center gap-3">

              {!isGuest && (
                <span className="text-sm text-gray-300 hidden md:inline">{user?.email}</span>
              )}
              <button
                onClick={handleLogout}
                className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition-colors cursor-pointer hidden md:block"
              >
                Cerrar Sesion
              </button>

              {/* Hamburger button (visible on mobile) */}
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden text-white p-1 cursor-pointer hover:bg-gray-700 rounded"
                aria-label="Abrir menu"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {mobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            </div>
          </div>

          {/* Mobile menu dropdown */}
          {mobileMenuOpen && (
            <div className="md:hidden mt-3 pt-3 border-t border-gray-700 flex flex-col gap-2">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `px-3 py-2 rounded ${isActive ? 'bg-gray-600' : 'hover:bg-gray-700'}`
                  }
                >
                  {item.label}
                  {item.to === '/pedidos' && <NotificationBadge />}
                </NavLink>
              ))}

              {!isGuest && (
                <span className="px-3 py-1 text-sm text-gray-400">{user?.email}</span>
              )}
              <button
                onClick={() => { handleLogout(); setMobileMenuOpen(false); }}
                className="mx-3 mb-2 bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition-colors cursor-pointer"
              >
                Cerrar Sesion
              </button>
            </div>
          )}
        </nav>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <AppRoutes
            roles={roles}
            isGuest={isGuest}
            isClient={isClient}
            isStock={isStock}
            isPedidos={isPedidos}
          />
        </main>

        <SessionTimeoutModal />
        <ToastContainer />
      </div>
  )
}

export default App
