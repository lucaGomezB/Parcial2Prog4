/**
 * AppRouter — Pure component that returns role-based route definitions.
 *
 * Receives role flags as props and returns <Routes> with the appropriate
 * route set for each role. No side effects, no state, no API calls.
 *
 * All page imports use React.lazy for code splitting by route.
 * Each <Routes> block is wrapped in <Suspense> with a spinner fallback.
 *
 * Cross-feature imports follow the rule: only API modules from other features.
 */
import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'

// ── Lazy page imports (code-split by route) ──

const CategoriasCRUD = lazy(() => import('@/features/categorias/pages/CategoriasCRUD'))
const IngredientesCRUD = lazy(() => import('@/features/productos/pages/IngredientesCRUD'))
const ProductosCRUD = lazy(() => import('@/features/productos/pages/ProductosCRUD'))
const ProductosCliente = lazy(() => import('@/features/productos/pages/ProductosCliente'))
const ProductoDetail = lazy(() => import('@/features/productos/pages/ProductoDetail'))
const Carrito = lazy(() => import('@/features/pedidos/pages/Carrito'))
const PedidosPage = lazy(() => import('@/features/pedidos/pages/PedidosPage'))
const DireccionesPage = lazy(() => import('@/features/pedidos/pages/DireccionesPage'))
const AdminFormasPagoPage = lazy(() => import('@/features/pedidos/pages/AdminFormasPagoPage'))
const AdminUsuariosPage = lazy(() => import('@/features/auth/pages/AdminUsuariosPage'))
const Dashboard = lazy(() => import('@/features/estadisticas/pages/Dashboard'))
const UnidadesMedidaAdminPage = lazy(() => import('@/features/unidades-medida/pages/UnidadesMedidaAdminPage'))
const Login = lazy(() => import('@/features/auth/pages/LoginConceptual'))
const PostPagoPage = lazy(() => import('@/features/pedidos/pages/PostPagoPage'))
const PedidoDetallePage = lazy(() => import('@/features/pedidos/pages/PedidoDetallePage'))

// ── Fallback ──

/** Simple centered spinner shown while a lazy route chunk is loading. */
function PageSkeleton() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

// ── Helpers ──

function hasRole(roles: string[], ...allowed: string[]) {
  return allowed.some((r) => roles.includes(r));
}

// ── Props ──

export interface AppRoutesProps {
  roles: string[]
  isGuest: boolean
  isClient: boolean
  isStock: boolean
  isPedidos: boolean
}

// ── Component ──

export function AppRoutes({ roles, isGuest, isClient, isStock, isPedidos }: AppRoutesProps) {
  const isAdmin = hasRole(roles, 'ADMIN');
  let productRole: 'admin' | 'stock' | 'pedidos' | 'client';
  if (isClient || isGuest) productRole = 'client';
  else if (hasRole(roles, 'ADMIN')) productRole = 'admin';
  else if (hasRole(roles, 'STOCK')) productRole = 'stock';
  else productRole = 'pedidos';

  if (isClient) {
    return (
      <Suspense fallback={<PageSkeleton />}>
        <Routes>
          <Route path="/" element={<Navigate to="/productos" replace />} />
          <Route path="/productos/:id" element={<ProductoDetail />} />
          <Route path="/productos" element={<ProductosCliente />} />
        {!isGuest && !isAdmin && <Route path="/carrito" element={<Carrito />} />}
          <Route path="/pedidos" element={<PedidosPage />} />
          <Route path="/pedidos/post-pago" element={<PostPagoPage />} />
          <Route path="/pedidos/:id" element={<PedidoDetallePage />} />
          <Route path="/direcciones" element={<DireccionesPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/productos" replace />} />
        </Routes>
      </Suspense>
    );
  }
  if (isStock) {
    return (
      <Suspense fallback={<PageSkeleton />}>
        <Routes>
          <Route path="/" element={<Navigate to="/productos" replace />} />
          <Route path="/productos" element={<ProductosCRUD role={productRole} />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/productos" replace />} />
        </Routes>
      </Suspense>
    );
  }
  if (isPedidos) {
    return (
      <Suspense fallback={<PageSkeleton />}>
        <Routes>
          <Route path="/" element={<Navigate to="/pedidos" replace />} />
          <Route path="/pedidos" element={<PedidosPage />} />
          <Route path="/pedidos/post-pago" element={<PostPagoPage />} />
          <Route path="/pedidos/:id" element={<PedidoDetallePage />} />
          <Route path="/login" element={<Login />} />
          <Route path="*" element={<Navigate to="/pedidos" replace />} />
        </Routes>
      </Suspense>
    );
  }
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/" element={<Navigate to="/productos" replace />} />
        <Route path="/categorias" element={<CategoriasCRUD />} />
        <Route path="/ingredientes" element={<IngredientesCRUD />} />
        <Route path="/admin/usuarios" element={<AdminUsuariosPage />} />
        <Route path="/admin/formas-pago" element={<AdminFormasPagoPage />} />
        <Route path="/admin/dashboard" element={<Dashboard />} />
        <Route path="/admin/unidades-medida" element={<UnidadesMedidaAdminPage />} />
        <Route path="/productos/:id" element={<ProductoDetail />} />
        <Route path="/productos" element={
          productRole === 'client' ? <ProductosCliente /> : <ProductosCRUD role={productRole} />
        } />
        {/* ADMIN no puede crear pedidos: /carrito y /checkout estan bloqueados */}
        {!isGuest && !isAdmin && <Route path="/carrito" element={<Carrito />} />}
        <Route path="/pedidos" element={<PedidosPage />} />
        <Route path="/pedidos/post-pago" element={<PostPagoPage />} />
        <Route path="/pedidos/:id" element={<PedidoDetallePage />} />
        <Route path="/direcciones" element={<DireccionesPage />} />
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/productos" replace />} />
      </Routes>
    </Suspense>
  );
}

/**
 * UnauthenticatedRoutes — Only shown when roles === null.
 * Only the login page is accessible; everything else redirects to /login.
 */
export function UnauthenticatedRoutes() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Suspense>
  )
}
