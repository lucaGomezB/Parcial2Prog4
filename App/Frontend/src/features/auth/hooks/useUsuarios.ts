import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usuariosApi } from '../api/usuarios'
import type { Usuario, UsuarioCreate, UsuarioUpdate } from '../api/usuarios'
import { queryKeys } from '@/shared/api/queryKeys'
import { apiFetchPaginatedFull, type PaginatedResponse } from '@/shared/api/client'

/** Fetches all usuarios with pagination and optional filters. Returns full response with total. */
export function useUsuarios(skip = 0, limit = 10, rolCodigo?: string, search?: string) {
  return useQuery<PaginatedResponse<Usuario>>({
    queryKey: [queryKeys.usuarios.all[0], 'list', { skip, limit, rolCodigo, search }] as const,
    queryFn: () => {
      let url = `/usuarios/?skip=${skip}&limit=${limit}`;
      if (rolCodigo) url += `&rol_codigo=${rolCodigo}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      return apiFetchPaginatedFull<Usuario>(url);
    },
  })
}

/** Fetches a single usuario by ID. Query is disabled when id is falsy. */
export function useUsuario(id: number) {
  return useQuery({
    queryKey: [queryKeys.usuarios.all[0], 'detail', id] as const,
    queryFn: () => usuariosApi.getById(id),
    enabled: !!id,
  })
}

/** Creates a new usuario via mutation. Invalidates the usuarios list cache on success. */
export function useCreateUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UsuarioCreate) => usuariosApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.usuarios.all }),
  })
}

/** Updates an existing usuario via mutation. Accepts { id, data }. Invalidates cache on success. */
export function useUpdateUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UsuarioUpdate }) => usuariosApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.usuarios.all }),
  })
}

/** Soft-deletes a usuario by ID via mutation. Invalidates the usuarios list cache on success. */
export function useDeleteUsuario() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => usuariosApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.usuarios.all }),
  })
}
