import { useQuery } from "@tanstack/react-query";
import { formasPagoApi } from "@/features/pedidos/api/formasPago";
import { queryKeys } from "@/shared/api/queryKeys";

/**
 * Fetches payment methods visible to the authenticated user.
 *
 * CLIENT users receive only habilitado=True methods (backend enforces this).
 * ADMIN/PEDIDOS users receive all methods based on incluir_deshabilitadas
 * query parameter.
 *
 * staleTime: 5 minutes — payment methods change rarely (only when an admin
 * toggles habilitado via the admin panel).
 */
export function useFormasPago() {
  return useQuery({
    queryKey: queryKeys.formasPago.all,
    queryFn: () => formasPagoApi.getAll(),
    staleTime: 5 * 60 * 1000, // 5 min
  });
}
