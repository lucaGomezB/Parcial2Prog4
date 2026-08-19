import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ingredientesApi } from '../api/ingredientes'
import type { Ingrediente, IngredienteCreate, IngredienteUpdate } from '../api/ingredientes'
import { queryKeys } from '@/shared/api/queryKeys'
import { apiFetchPaginatedFull, type PaginatedResponse } from '@/shared/api/client'

/** Fetches all ingredientes with pagination (skip/limit) and optional text search. Returns full response with total. */
export function useIngredientes(skip = 0, limit = 10, search?: string) {
  let url = `/ingredientes/?skip=${skip}&limit=${limit}`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  return useQuery<PaginatedResponse<Ingrediente>>({
    queryKey: [...queryKeys.ingredientes.all, skip, limit, search] as const,
    queryFn: () => apiFetchPaginatedFull<Ingrediente>(url),
  })
}

/** Fetches a single ingrediente by its ID. Query is disabled when id is falsy. */
export function useIngrediente(id: number) {
  return useQuery({
    queryKey: [...queryKeys.ingredientes.all, 'detail', id] as const,
    queryFn: () => ingredientesApi.getById(id),
    enabled: !!id,
  })
}

/** Creates a new ingrediente via mutation. Invalidates the ingredientes cache on success. */
export function useCreateIngrediente() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: IngredienteCreate) => ingredientesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.ingredientes.all }),
  })
}

/** Updates an existing ingrediente via mutation. Accepts { id, data }. Invalidates cache on success. */
export function useUpdateIngrediente() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: IngredienteUpdate }) => ingredientesApi.update(id, data as Parameters<typeof ingredientesApi.update>[1]),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.ingredientes.all }),
  })
}

/** Deletes an ingrediente by ID via mutation. Invalidates the ingredientes cache on success. */
export function useDeleteIngrediente() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => ingredientesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.ingredientes.all }),
  })
}
