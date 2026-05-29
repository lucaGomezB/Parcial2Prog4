import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import CategoriasCRUD from './pages/CategoriasCRUD'
import IngredientesCRUD from './pages/IngredientesCRUD'
import ProductosCRUD from './pages/ProductosCRUD'
import Carrito from './pages/Carrito'
import PedidosPage from './pages/PedidosPage'
import DireccionesPage from './pages/DireccionesPage'
import AdminUsuariosPage from './pages/AdminUsuariosPage'
import SessionTimeoutModal from './components/SessionTimeoutModal'
import Login from './pages/LoginConceptual'
import { clearAuth, getAccessToken, apiFetch, getUserInfo } from './api/client'
import { getItemCount } from './utils/carrito'

/* ── Helpers ── */
function hasRole(roles: string[], ...allowed: string[]) {
  return allowed.some((r) => roles.includes(r));
}

function App() {
  const [userRoles, setUserRoles] = useState<string[] | null>(null)
  const [verifying, setVerifying] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    async function checkAuth() {
      const token = getAccessToken()

      if (!token) {
        // Sin token → invitado
        setUserRoles([])
        setVerifying(false)
        return
      }

      // Hay token → verificar contra backend
      try {
        await apiFetch('/auth/me')
        const user = getUserInfo()
        setUserRoles(user?.roles ?? [])
      } catch {
        // Token expirado o inválido
        clearAuth()
        setUserRoles(null)
      }
      setVerifying(false)
    }

    checkAuth()
  }, [])

  // ── Escuchar evento auth:login-required desde SessionTimeoutModal ──
  useEffect(() => {
    const handler = () => setUserRoles(null);
    window.addEventListener('auth:login-required', handler);
    return () => window.removeEventListener('auth:login-required', handler);
  }, []);

  const handleLogout = async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } catch {
      // Si falla, igual limpiamos localmente
    }
    clearAuth()
    setUserRoles(null)
    navigate('/login')
  }

  if (verifying) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <p className="text-gray-500">Verificando sesion...</p>
      </div>
    )
  }

  if (userRoles === null) {
    return (
      <Routes>
        <Route path="/login" element={<Login onLogin={(roles) => setUserRoles(roles)} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  const isGuest = !getAccessToken();
  const isClient = !isGuest && !hasRole(userRoles, 'ADMIN', 'STOCK', 'PEDIDOS')
  const canSeeFullNav = hasRole(userRoles, 'ADMIN', 'PEDIDOS')
  const isAdmin = hasRole(userRoles, 'ADMIN')

  const cartCount = getItemCount()
  const hasGestorRole = hasRole(userRoles, 'ADMIN', 'PEDIDOS')

  let navItems: { to: string; label: string }[];
  if (isClient) {
    navItems = [
      { to: '/productos', label: 'Menú' },
      { to: '/pedidos', label: 'Mis Pedidos' },
      { to: '/direcciones', label: 'Direcciones' },
      ...(isGuest ? [] : [{ to: '/carrito', label: `Carrito${cartCount > 0 ? ` (${cartCount})` : ''}` }]),
    ];
  } else if (canSeeFullNav) {
    navItems = [
      { to: '/categorias', label: 'Categorías' },
      { to: '/ingredientes', label: 'Ingredientes' },
      { to: '/productos', label: 'Productos' },
      { to: '/pedidos', label: 'Pedidos' },
      { to: '/direcciones', label: 'Direcciones' },
      ...(isGuest ? [] : [{ to: '/carrito', label: `Carrito${cartCount > 0 ? ` (${cartCount})` : ''}` }]),
    ];
    if (isAdmin) {
      navItems.splice(0, 0, { to: '/admin/usuarios', label: 'Usuarios' });
    }
  } else {
    navItems = [
      { to: '/productos', label: 'Productos' },
      { to: '/pedidos', label: 'Pedidos' },
      { to: '/direcciones', label: 'Direcciones' },
      ...(isGuest ? [] : [{ to: '/carrito', label: `Carrito${cartCount > 0 ? ` (${cartCount})` : ''}` }]),
    ];
  }

  return (
    <div className="min-h-screen bg-white">
      <nav className="bg-gray-800 text-white px-4 py-3 flex justify-between items-center">
        <div className="flex gap-4 items-center">
          <span className="font-bold mr-4">{isClient ? 'Menú' : 'Catálogo de Productos'}</span>
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
            if (isClient) productRole = 'client';
            else if (hasRole(userRoles, 'ADMIN')) productRole = 'admin';
            else if (hasRole(userRoles, 'STOCK')) productRole = 'stock';
            else productRole = 'pedidos';

            return isClient ? (
              <>
                <Route path="/" element={<Navigate to="/productos" replace />} />
                <Route path="/productos" element={<ProductosCRUD role={productRole} />} />
                {!isGuest && <Route path="/carrito" element={<Carrito />} />}
                <Route path="/pedidos" element={<PedidosPage />} />
                <Route path="/direcciones" element={<DireccionesPage />} />
                <Route path="*" element={<Navigate to="/productos" replace />} />
              </>
            ) : (
              <>
                <Route path="/" element={<Navigate to="/productos" replace />} />
                {canSeeFullNav && <Route path="/categorias" element={<CategoriasCRUD />} />}
                {canSeeFullNav && <Route path="/ingredientes" element={<IngredientesCRUD />} />}
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
