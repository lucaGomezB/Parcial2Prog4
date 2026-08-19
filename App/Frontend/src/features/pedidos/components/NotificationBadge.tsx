/**
 * NotificationBadge — Red badge showing count of active pedidos.
 *
 * Self-contained: calls useActivePedidosCount() internally.
 * Used in navbar (desktop + mobile) to indicate pending orders.
 * Only visible when count > 0.
 */
import { useActivePedidosCount } from '@/features/pedidos/hooks/useActivePedidosCount'

export function NotificationBadge() {
  const count = useActivePedidosCount()

  if (count <= 0) return null

  return (
    <span className="ml-1 inline-flex items-center justify-center bg-red-500 text-white text-xs font-bold rounded-full min-w-[18px] h-[18px] px-1">
      {count > 99 ? '99+' : count}
    </span>
  )
}
