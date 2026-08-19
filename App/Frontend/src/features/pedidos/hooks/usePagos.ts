import { useQuery } from '@tanstack/react-query'
import { useRef } from 'react'
import { pagosApi, type PaymentStatusResponse } from '../api/pagos'
import { queryKeys } from '@/shared/api/queryKeys'

/** Fetches all pagos for a given pedido ID. Query is disabled when pedidoId is falsy. */
export function usePagosByPedido(pedidoId: number) {
  return useQuery({
    queryKey: queryKeys.pagos.byPedido(pedidoId),
    queryFn: () => pagosApi.getPagosByPedido(pedidoId),
    enabled: !!pedidoId,
  })
}

const MAX_POLL_ATTEMPTS = 5

/**
 * Polls GET /pagos/status every 2 seconds for up to 10 seconds (5 attempts).
 *
 * Used by PostPagoPage after MercadoPago redirect.
 * Returns the latest status response plus polling metadata.
 * After MAX_POLL_ATTEMPTS, polling stops — no more HTTP requests are sent.
 */
export function usePagoStatus(externalReference: string) {
  const attemptRef = useRef(0)

  const query = useQuery<PaymentStatusResponse>({
    queryKey: ['pagos', 'status', externalReference],
    queryFn: () => {
      attemptRef.current += 1
      return pagosApi.getPaymentStatus(externalReference)
    },
    refetchInterval: () => {
      if (attemptRef.current >= MAX_POLL_ATTEMPTS) return false
      return 2000
    },
    enabled: !!externalReference,
    retry: false,
  })

  const isPolling = query.isFetching && !query.isError
  const isTimeout = attemptRef.current >= MAX_POLL_ATTEMPTS && query.data?.status !== 'found'

  return {
    status: query.data?.status ?? null,
    pedidoId: query.data?.pedido_id ?? null,
    mpStatus: query.data?.mp_status ?? null,
    apiError: query.data?.error ?? null,
    isPolling,
    isTimeout,
    error: query.error,
  }
}
