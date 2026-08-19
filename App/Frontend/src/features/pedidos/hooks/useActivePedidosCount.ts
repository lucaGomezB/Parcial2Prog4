import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '@/shared/api/client'
import { useAuthStore } from '@/shared/store/authStore'

interface ActivePedidosResponse {
  total: number
}

/**
 * Returns the count of active pedidos (non-terminal states).
 * Used for the navbar badge. Refreshes every 30 seconds.
 *
 * Robustness: the count must never get "stuck". We therefore:
 * - scope the query key by user id, so switching sessions (login/logout as a
 *   different user) never serves another user's cached count;
 * - poll even when the tab is in the background (refetchIntervalInBackground),
 *   because the payment flow opens another tab and backgrounds this one;
 * - re-sync as soon as the tab regains focus (refetchOnWindowFocus), overriding
 *   the global `refetchOnWindowFocus: false`;
 * - re-sync after the browser reconnects to the network (refetchOnReconnect).
 */
export function useActivePedidosCount() {
  const userId = useAuthStore((s) => s.user?.id)

  const { data } = useQuery<ActivePedidosResponse>({
    queryKey: ['pedidos', 'activos', 'count', userId ?? 'guest'],
    queryFn: () => apiFetch<ActivePedidosResponse>('/pedidos/activos?limit=1'),
    enabled: userId != null,
    refetchInterval: 30_000,
    refetchIntervalInBackground: true,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
    staleTime: 15_000,
  })
  return data?.total ?? 0
}
