import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { direccionesApi } from '../api/direcciones'
import type { DireccionEntregaInput, DireccionEntregaUpdate } from '../api/direcciones'
import { queryKeys } from '@/shared/api/queryKeys'

/** Fetches all direcciones de entrega for the authenticated user. Uses TanStack Query.
 *  When incluirLocales=true, also returns company stores (es_local=True) for pickup. */
export function useDirecciones(incluirLocales = false) {
  return useQuery({
    queryKey: incluirLocales ? [...queryKeys.direcciones.all, 'incluir_locales'] : queryKeys.direcciones.all,
    queryFn: () => direccionesApi.getAll(incluirLocales),
  })
}

/** Creates a new direccion de entrega via mutation. Invalidates the direcciones cache on success. */
export function useCreateDireccion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: DireccionEntregaInput) => direccionesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.direcciones.all }),
  })
}

/** Updates an existing direccion via mutation. Accepts { id, data }. Invalidates cache on success. */
export function useUpdateDireccion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DireccionEntregaUpdate }) => direccionesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.direcciones.all }),
  })
}

/** Deletes a direccion by ID via mutation. Invalidates the direcciones cache on success. */
export function useDeleteDireccion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => direccionesApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.direcciones.all }),
  })
}

/** Sets a direccion as the principal (default) for the authenticated user via mutation. Invalidates cache on success. */
export function useSetPrincipalDireccion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => direccionesApi.setPrincipal(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.direcciones.all }),
  })
}
