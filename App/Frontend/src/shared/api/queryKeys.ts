/**
 * Centralized TanStack Query key factory.
 *
 * Convention: each domain object groups its keys under a top-level property.
 * Keys are structured as hierarchical tuples (e.g., ['productos', 'detail', id])
 * so that invalidating a parent key (e.g., ['productos']) cascades to all children.
 *
 * Functions returning keys (e.g., `detail(id)`) allow type-safe parameterization.
 * All tuple segments use `as const` so TypeScript infers literal types for query-key
 * matching in useQuery / useMutation.
 */
export const queryKeys = {
  productos: {
    all: ['productos'] as const,
    list: (filters?: Record<string, unknown>) => ['productos', 'list', filters] as const,
    detail: (id: number) => ['productos', 'detail', id] as const,
    ingredientes: (productoId: number) => ['productos', 'ingredientes', productoId] as const,
  },
  categorias: {
    all: ['categorias'] as const,
    tree: ['categorias', 'tree'] as const,
  },
  ingredientes: {
    all: ['ingredientes'] as const,
    productosAfectados: (ingredienteId: number) => ['ingredientes', 'productosAfectados', ingredienteId] as const,
  },
  pedidos: {
    all: ['pedidos'] as const,
    activos: ['pedidos', 'activos'] as const,
    historial: ['pedidos', 'historial'] as const,
    detail: (id: number) => ['pedidos', 'detail', id] as const,
  },
  usuarios: {
    all: ['usuarios'] as const,
  },
  estadisticas: {
    all: ['estadisticas'] as const,
    resumen: ['estadisticas', 'resumen'] as const,
    ventasPeriodo: (desde: string, hasta: string) => ['estadisticas', 'ventasPeriodo', desde, hasta] as const,
    productosTop: ['estadisticas', 'productosTop'] as const,
    pedidosEstado: ['estadisticas', 'pedidosEstado'] as const,
    ingresosFormaPago: (desde: string, hasta: string) => ['estadisticas', 'ingresosFormaPago', desde, hasta] as const,
  },
  direcciones: {
    all: ['direcciones'] as const,
  },
  pagos: {
    byPedido: (pedidoId: number) => ['pagos', 'byPedido', pedidoId] as const,
  },
  formasPago: {
    all: ['formasPago'] as const,
  },
};
