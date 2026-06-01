import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import CategoriasCRUD from './pages/CategoriasCRUD'
import IngredientesCRUD from './pages/IngredientesCRUD'
import ProductosCRUD from './pages/ProductosCRUD'
import Carrito from './pages/Carrito'
import PedidosPage from './pages/PedidosPage'
import DireccionesPage from './pages/DireccionesPage'
import AdminUsuariosPage from './pages/AdminUsuariosPage'
import SessionTimeoutModal from './components/SessionTimeoutModal'
import Login from './pages/LoginConceptual'
import { apiFetch, getAccessToken, refreshSession } from './api/client'
import type { UserInfo } from './api/client'
import { getItemCount } from './utils/carrito'
import { useAuthStore } from './store/authStore'

/* ── Helpers ── */

/**
 * Checks whether any of the allowed roles are present in the user's role list.
 * Used for role-based access control (RBAC) throughout the navigation and route logic.
 */
function hasRole(roles: string[], ...allowed: string[]) {
  return allowed.some((r) => roles.includes(r));
}

/**
 * Root application component.
 *
 * Responsibilities:
 *  - Bootstrap session verification on mount (checks for an httpOnly refresh cookie).
 *  - Renders a loading screen while the session is being verified.
 *  - Shows the login page when no session exists (roles === null).
 *  - Once authenticated/verified, renders the full layout: navigation bar,
 *    role-appropriate route definitions, and a session timeout modal.
 *
 * Three-state role pattern:
 *   roles = null  → not yet determined (initial loading)
 *   roles = []    → guest / unauthenticated (browsing without token)
 *   roles = [...] → authenticated with specific roles (e.g. ["ADMIN", "CLIENTE"])
 */
function App() {
  const [verifying, setVerifying] = useState(true)
  const roles = useAuthStore((s) => s.roles)
  const user = useAuthStore((s) => s.user)
  const navigate = useNavigate()

  /**
   * Bootstrap effect: runs once on mount.
   *
   * Attempts to restore the session by calling the refresh endpoint.
   * The backend stores the refresh token in an httpOnly cookie, so no
   * client-side storage of sensitive tokens is needed.
   *
   * Flow:
   *   1. Call refreshSession() — if it fails, there is no active session.
   *   2. On success, fetch user info from /auth/me to populate the store.
   *   3. If /auth/me fails, the 401 interceptor in client.ts already
   *      clears the store via logout().
   */
  useEffect(() => {
    async function bootstrap() {
      const hasSession = await refreshSession()

      if (!hasSession) {
        useAuthStore.getState().logout()
        setVerifying(false)
        return
      }

      try {
        const user = await apiFetch<UserInfo>('/auth/me')
        useAuthStore.getState().setUser(user)
      } catch {
        // Interceptor already called store.logout() if token is invalid.
      }
      setVerifying(false)
    }

    bootstrap()
  }, [])

  /**
   * Logs the user out both on the server and locally.
   * POSTs to /auth/logout to invalidate the refresh token on the backend,
   * then clears the local Zustand store and redirects to the login page.
   */
  const handleLogout = async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } catch {
      // If the server call fails, still clear local state to prevent lockout.
    }
    useAuthStore.getState().logout()
    navigate('/login')
  }

  // ── Loading state: show a centered spinner while verifying the session ──
  if (verifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <p className="text-gray-500">Verificando sesion...</p>
      </div>
    )
  }

  // ── Unauthenticated state: only the login route is accessible ──
  if (roles === null) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  // ── Authenticated/guest state: resolve role-based capabilities ──
  const isGuest = !getAccessToken();
  const isClient = !isGuest && !hasRole(roles, 'ADMIN', 'STOCK', 'PEDIDOS')
  const isAdmin = hasRole(roles, 'ADMIN')
  const isStock = hasRole(roles, 'STOCK')
  const isPedidos = hasRole(roles, 'PEDIDOS')

  const cartCount = getItemCount()

  // Build navigation items based on the user's role.
  let navItems: { to: string; label: string }[];
  if (isGuest) {
    navItems = [
      { to: '/productos', label: 'Menu' },
    ];
  } else if (isClient) {
    navItems = [
      { to: '/productos', label: 'Menu' },
      { to: '/pedidos', label: 'Mis Pedidos' },
      { to: '/direcciones', label: 'Direcciones' },
      { to: '/carrito', label: `Carrito${cartCount > 0 ? ` (${cartCount})` : ''}` },
    ];
  } else if (isStock) {
    navItems = [
      { to: '/productos', label: 'Productos' },
    ];
  } else if (isPedidos) {
    navItems = [
      { to: '/pedidos', label: 'Pedidos' },
    ];
  } else if (isAdmin) {
    navItems = [
      { to: '/categorias', label: 'Categorias' },
      { to: '/ingredientes', label: 'Ingredientes' },
      { to: '/productos', label: 'Productos' },
      { to: '/pedidos', label: 'Pedidos' },
      { to: '/direcciones', label: 'Direcciones' },
      { to: '/carrito', label: `Carrito${cartCount > 0 ? ` (${cartCount})` : ''}` },
    ];
    // Admin gets the user management page first in the nav order.
    navItems.splice(0, 0, { to: '/admin/usuarios', label: 'Usuarios' });
  } else {
    // Fallback for any unrecognized role combination.
    navItems = [
      { to: '/productos', label: 'Productos' },
      { to: '/pedidos', label: 'Pedidos' },
      { to: '/direcciones', label: 'Direcciones' },
      { to: '/carrito', label: `Carrito${cartCount > 0 ? ` (${cartCount})` : ''}` },
    ];
  }

  return (
    <div className="min-h-screen bg-white">
      {/*
       * Top navigation bar.
       * Uses NavLink from react-router-dom for automatic active-link styling.
       * The brand label changes based on whether the user is a client or staff.
       */}
      <nav className="bg-gray-800 text-white px-4 py-3 flex justify-between items-center">
        <div className="flex gap-4 items-center">
          <span className="font-bold mr-4">{isClient || isGuest ? 'Menu' : 'Catalogo de Productos'}</span>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `px-3 py-1 rounded ${isActive ? 'bg-gray-600' : 'hover:bg-gray-700'}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
        <div className="flex items-center gap-4">
          {!isGuest && (
            <span className="text-sm text-gray-300">{user?.email}</span>
          )}
          <button 
            onClick={handleLogout}
            className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition-colors cursor-pointer"
          >
            Cerrar Sesion
          </button>
        </div>
      </nav>

      {/*
       * Main content area with role-based routing.
       *
       * Each role gets a different set of accessible routes:
       *   - Guest: only product listing (browsing).
       *   - Client: products, cart, orders, addresses.
       *   - Stock: product management.
       *   - Pedidos: order management.
       *   - Admin: full CRUD access to all entities.
       *
       * The inline IIFE pattern is used here to avoid a separate component
       * while keeping the route definitions role-conditional.
       */}
      <main>
        <Routes>
          {(() => {
            let productRole: 'admin' | 'stock' | 'pedidos' | 'client';
            if (isClient || isGuest) productRole = 'client';
            else if (hasRole(roles, 'ADMIN')) productRole = 'admin';
            else if (hasRole(roles, 'STOCK')) productRole = 'stock';
            else productRole = 'pedidos';

            if (isClient) {
              return (
                <>
                  <Route path="/" element={<Navigate to="/productos" replace />} />
                  <Route path="/productos" element={<ProductosCRUD role={productRole} />} />
                  {!isGuest && <Route path="/carrito" element={<Carrito />} />}
                  <Route path="/pedidos" element={<PedidosPage />} />
                  <Route path="/direcciones" element={<DireccionesPage />} />
                  <Route path="*" element={<Navigate to="/productos" replace />} />
                </>
              );
            }
            if (isStock) {
              return (
                <>
                  <Route path="/" element={<Navigate to="/productos" replace />} />
                  <Route path="/productos" element={<ProductosCRUD role={productRole} />} />
                  <Route path="*" element={<Navigate to="/productos" replace />} />
                </>
              );
            }
            if (isPedidos) {
              return (
                <>
                  <Route path="/" element={<Navigate to="/pedidos" replace />} />
                  <Route path="/pedidos" element={<PedidosPage />} />
                  <Route path="*" element={<Navigate to="/pedidos" replace />} />
                </>
              );
            }
            return (
              <>
                <Route path="/" element={<Navigate to="/productos" replace />} />
                <Route path="/categorias" element={<CategoriasCRUD />} />
                <Route path="/ingredientes" element={<IngredientesCRUD />} />
                <Route path="/admin/usuarios" element={<AdminUsuariosPage />} />
                <Route path="/productos" element={<ProductosCRUD role={productRole} />} />
                {!isGuest && <Route path="/carrito" element={<Carrito />} />}
                <Route path="/pedidos" element={<PedidosPage />} />
                <Route path="/direcciones" element={<DireccionesPage />} />
                <Route path="*" element={<Navigate to="/productos" replace />} />
              </>
            );
          })()}
        </Routes>
      </main>

      {/*
       * SessionTimeoutModal: displayed globally on top of all content.
       * It monitors user activity and warns before the token expires,
       * offering a chance to extend the session.
       */}
      <SessionTimeoutModal />
    </div>
  )
}

export default App
