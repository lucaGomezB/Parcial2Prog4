import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { pedidosApi } from '../api/pedidos'
import type { CreatePedidoInput } from '../api/pedidos'
import { queryKeys } from '@/shared/api/queryKeys'
import { apiFetchPaginatedFull, type PaginatedResponse } from '@/shared/api/client'
import type { Pedido } from '../api/pedidos'

/** Fetches all active (non-terminal) pedidos with pagination. Returns full response with total. */
export function usePedidosActivos(skip = 0, limit = 10, sortBy = "id", sortOrder: "asc" | "desc" = "desc", search?: string) {
  const searchParam = search ? `&search=${encodeURIComponent(search)}` : ""
  return useQuery<PaginatedResponse<Pedido>>({
    queryKey: [...queryKeys.pedidos.activos, skip, limit, sortBy, sortOrder, search ?? ""] as const,
    queryFn: () => apiFetchPaginatedFull<Pedido>(`/pedidos/activos?skip=${skip}&limit=${limit}&sort_by=${sortBy}&sort_order=${sortOrder}${searchParam}`),
  })
}

/** Fetches the pedidos historial (cancelled/completed) with pagination. Returns full response with total. */
export function usePedidosHistorial(skip = 0, limit = 10, sortBy = "id", sortOrder: "asc" | "desc" = "desc", search?: string) {
  const searchParam = search ? `&search=${encodeURIComponent(search)}` : ""
  return useQuery<PaginatedResponse<Pedido>>({
    queryKey: [...queryKeys.pedidos.historial, skip, limit, sortBy, sortOrder, search ?? ""] as const,
    queryFn: () => apiFetchPaginatedFull<Pedido>(`/pedidos/historial?skip=${skip}&limit=${limit}&sort_by=${sortBy}&sort_order=${sortOrder}${searchParam}`),
  })
}

/** Fetches the authenticated user's own pedidos with pagination. Returns full response with total. */
export function useMisPedidos(skip = 0, limit = 10) {
  return useQuery<PaginatedResponse<Pedido>>({
    queryKey: ['pedidos', 'misPedidos', skip, limit] as const,
    queryFn: () => apiFetchPaginatedFull<Pedido>(`/pedidos/mis-pedidos?skip=${skip}&limit=${limit}`),
  })
}

/** Fetches a single pedido by its ID. Query is disabled when id is falsy. */
export function usePedido(id: number) {
  return useQuery({
    queryKey: queryKeys.pedidos.detail(id),
    queryFn: () => pedidosApi.getById(id),
    enabled: !!id,
  })
}

/** Fetches the estado-change historial for a given pedido ID. Query disabled when pedidoId is falsy. */
export function useHistorialPedido(pedidoId: number) {
  return useQuery({
    queryKey: [...queryKeys.pedidos.detail(pedidoId), 'historial'],
    queryFn: () => pedidosApi.getHistorialById(pedidoId),
    enabled: !!pedidoId,
  })
}

/** Creates a new pedido via mutation. Invalidates the pedidos list cache on success. */
export function useCreatePedido() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreatePedidoInput) => pedidosApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.pedidos.all })
    },
  })
}

/** Advances a pedido to the next estado in the FSM via mutation. Invalidates cache on success. */
export function useAvanzarPedido() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => pedidosApi.avanzar(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.pedidos.all })
    },
  })
}

/** Cancels a pedido with a motivo string via mutation. Invalidates the pedidos cache on success. */
export function useCancelarPedido() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, motivo }: { id: number; motivo: string }) => pedidosApi.cancelar(id, motivo),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.pedidos.all })
    },
  })
}

/** Updates a pedido detalle line (productoId, cantidad) via mutation. Invalidates cache on success. */
export function useActualizarDetalle() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ pedidoId, productoId, cantidad }: { pedidoId: number; productoId: number; cantidad: number }) =>
      pedidosApi.actualizarDetalle(pedidoId, productoId, cantidad),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.pedidos.all })
    },
  })
}
