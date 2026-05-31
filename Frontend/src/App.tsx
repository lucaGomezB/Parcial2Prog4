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
function hasRole(roles: string[], ...allowed: string[]) {
  return allowed.some((r) => roles.includes(r));
}

function App() {
  const [verifying, setVerifying] = useState(true)
  const roles = useAuthStore((s) => s.roles)
  const navigate = useNavigate()

  useEffect(() => {
    async function bootstrap() {
      // Intentar renovar sesión vía cookie httpOnly (refresh token)
      const hasSession = await refreshSession()

      if (!hasSession) {
        // Sin sesión activa → login
        useAuthStore.getState().logout()
        setVerifying(false)
        return
      }

      // Sesión renovada → obtener datos del usuario
      try {
        const user = await apiFetch<UserInfo>('/auth/me')
        useAuthStore.getState().setUser(user)
      } catch {
        // El interceptor ya llamó store.logout() si falló
      }
      setVerifying(false)
    }

    bootstrap()
  }, [])

  const handleLogout = async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } catch {
      // Si falla, igual limpiamos localmente
    }
    useAuthStore.getState().logout()
    navigate('/login')
  }

  if (verifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <p className="text-gray-500">Verificando sesion...</p>
      </div>
    )
  }

  // ── roles === null → necesita login (nunca autenticado o después de logout) ──
  if (roles === null) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  // ── Desde acá roles es string[] (invitado o autenticado) ──
  const isGuest = !getAccessToken();
  const isClient = !isGuest && !hasRole(roles, 'ADMIN', 'STOCK', 'PEDIDOS')
  const isAdmin = hasRole(roles, 'ADMIN')
  const isStock = hasRole(roles, 'STOCK')
  const isPedidos = hasRole(roles, 'PEDIDOS')

  const cartCount = getItemCount()

  let navItems: { to: string; label: string }[];
  if (isGuest) {
    navItems = [
      { to: '/productos', label: 'Menú' },
    ];
  } else if (isClient) {
    navItems = [
      { to: '/productos', label: 'Menú' },
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
      { to: '/categorias', label: 'Categorías' },
      { to: '/ingredientes', label: 'Ingredientes' },
      { to: '/productos', label: 'Productos' },
      { to: '/pedidos', label: 'Pedidos' },
      { to: '/direcciones', label: 'Direcciones' },
      { to: '/carrito', label: `Carrito${cartCount > 0 ? ` (${cartCount})` : ''}` },
    ];
    navItems.splice(0, 0, { to: '/admin/usuarios', label: 'Usuarios' });
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
      <nav className="bg-gray-800 text-white px-4 py-3 flex justify-between items-center">
        <div className="flex gap-4 items-center">
          <span className="font-bold mr-4">{isClient || isGuest ? 'Menú' : 'Catálogo de Productos'}</span>
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
        <button 
          onClick={handleLogout}
          className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm transition-colors cursor-pointer"
        >
          Cerrar Sesión
        </button>
      </nav>

      <main>
        <Routes>
          {(() => {
            // Determinar el role para ProductosCRUD según los roles del usuario
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
      <SessionTimeoutModal />
    </div>
  )
}

export default App
