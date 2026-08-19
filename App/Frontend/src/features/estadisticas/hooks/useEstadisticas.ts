import { useQuery } from '@tanstack/react-query'
import {
  fetchResumen,
  fetchVentasPeriodo,
  fetchProductosTop,
  fetchPedidosEstado,
  fetchIngresosFormaPago,
} from '../api/estadisticas'
import { queryKeys } from '@/shared/api/queryKeys'

/** Fetches the dashboard resumen KPIs (total pedidos, ventas, activos, etc.). Refreshes every 60s. */
export function useResumen() {
  return useQuery({
    queryKey: queryKeys.estadisticas.resumen,
    queryFn: () => fetchResumen(),
    refetchInterval: 60_000,
  })
}

/** Fetches ventas aggregated by a period (dia/semana/mes) between two dates. Disabled if dates are falsy. */
export function useVentasPeriodo(desde: string, hasta: string, agrupacion: string) {
  return useQuery({
    queryKey: queryKeys.estadisticas.ventasPeriodo(desde, hasta),
    queryFn: () => fetchVentasPeriodo(desde, hasta, agrupacion),
    enabled: !!desde && !!hasta,
    refetchInterval: 60_000,
  })
}

/** Fetches the top N productos by ingresos (default 10). Refreshes every 60s. */
export function useProductosTop(limit: number = 10) {
  return useQuery({
    queryKey: queryKeys.estadisticas.productosTop,
    queryFn: () => fetchProductosTop(limit),
    refetchInterval: 60_000,
  })
}

/** Fetches pedido counts grouped by estado for the dashboard charts. Refreshes every 60s. */
export function usePedidosEstado() {
  return useQuery({
    queryKey: queryKeys.estadisticas.pedidosEstado,
    queryFn: () => fetchPedidosEstado(),
    refetchInterval: 60_000,
  })
}

/** Fetches ingresos grouped by forma de pago between two dates. Disabled if dates are falsy. Refreshes every 60s. */
export function useIngresosFormaPago(desde: string, hasta: string) {
  return useQuery({
    queryKey: queryKeys.estadisticas.ingresosFormaPago(desde, hasta),
    queryFn: () => fetchIngresosFormaPago(desde, hasta),
    enabled: !!desde && !!hasta,
    refetchInterval: 60_000,
  })
}
