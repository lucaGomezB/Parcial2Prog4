import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productosApi } from '../api/productos'
import type { Producto, ProductoCreate, ProductoUpdate } from '../api/productos'
import { queryKeys } from '@/shared/api/queryKeys'
import { apiFetchPaginatedFull, type PaginatedResponse } from '@/shared/api/client'

/** Fetches all productos with pagination (skip/limit), optional text search, category filter, and server-side sort. Returns full response with total.
 *  Accepts optional extraOptions (refetchInterval, staleTime, enabled) forwarded to useQuery. */
export function useProductos(
  skip = 0, limit = 10, search?: string, categoriaIds?: number[], sortBy?: string, sortOrder?: string,
  extraOptions?: { refetchInterval?: number; staleTime?: number; enabled?: boolean }
) {
  let url = `/productos/?skip=${skip}&limit=${limit}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (categoriaIds && categoriaIds.length > 0) {
    for (const cid of categoriaIds) {
      url += `&categoria_id=${cid}`;
    }
  }
  if (sortBy) {
    url += `&sort_by=${encodeURIComponent(sortBy)}`;
    url += `&sort_order=${sortOrder === 'asc' ? 'asc' : 'desc'}`;
  }
  return useQuery<PaginatedResponse<Producto>>({
    queryKey: queryKeys.productos.list({ skip, limit, search, categoriaIds, sortBy, sortOrder }),
    queryFn: () => apiFetchPaginatedFull<Producto>(url),
    ...extraOptions,
  })
}

/** Fetches a single producto by its ID. Query is disabled when id is falsy. */
export function useProducto(id: number) {
  return useQuery({
    queryKey: queryKeys.productos.detail(id),
    queryFn: () => productosApi.getById(id),
    enabled: !!id,
  })
}

/** Creates a new producto via mutation. Invalidates the productos list cache on success. */
export function useCreateProducto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProductoCreate) => productosApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.productos.all }),
  })
}

/** Updates an existing producto via mutation. Accepts { id, data }. Invalidates cache on success. */
export function useUpdateProducto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductoUpdate }) => productosApi.update(id, data as Parameters<typeof productosApi.update>[1]),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.productos.all }),
  })
}

/** Fetches ingredients for a single producto by its ID. Query disabled when productoId is falsy. */
export function useProductoIngredientes(productoId: number) {
  return useQuery({
    queryKey: queryKeys.productos.ingredientes(productoId),
    queryFn: () => productosApi.getIngredientes(productoId),
    enabled: !!productoId,
  })
}

/** Soft-deletes a producto by ID via mutation. Invalidates the productos list cache on success. */
export function useDeleteProducto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => productosApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.productos.all }),
  })
}
