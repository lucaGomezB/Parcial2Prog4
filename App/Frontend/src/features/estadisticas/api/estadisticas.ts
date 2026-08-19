/**
 * Estadisticas API functions for the admin dashboard.
 *
 * Provides typed fetch functions for all 5 dashboard endpoints.
 * All monetary values are typed as `string` because the backend serializes
 * Decimal values, and Axios parses JSON numbers as JavaScript numbers which
 * can lose precision. The Dashboard page formats them using toLocaleString('es-AR').
 */
import { apiFetch } from "@/shared/api/client";

// ── Types ──

/** KPI summary returned by GET /estadisticas/resumen. */
export interface ResumenResponse {
  ventas_hoy: string;
  ticket_promedio: string;
  pedidos_activos: number;
  mes_actual: string;
}

/** Single data point for the ventas-periodo line chart. */
export interface VentasPeriodoItem {
  fecha: string;
  total: string;
}

/** A product ranked by total revenue across non-cancelled orders. */
export interface ProductoTopItem {
  producto_id: number;
  nombre: string;
  cantidad_vendida: number;
  ingresos: string;
}

/** Count of orders grouped by their current estado_codigo. */
export interface PedidosEstadoItem {
  estado_codigo: string;
  cantidad: number;
}

/** Revenue grouped by payment method (only approved payments). */
export interface IngresosResponse {
  forma_pago_codigo: string;
  total: string;
}

// ── API Functions ──

/**
 * Fetches the KPI summary for the dashboard.
 * Returns the 4 key indicators: today's sales, average ticket,
 * active orders count, and current month's total.
 */
export function fetchResumen() {
  return apiFetch<ResumenResponse>("/estadisticas/resumen");
}

/**
 * Fetches aggregated sales data for a date range, grouped by the given interval.
 *
 * @param desde - Start date as YYYY-MM-DD string (inclusive).
 * @param hasta - End date as YYYY-MM-DD string (inclusive).
 * @param agrupacion - Grouping interval: "day", "week", or "month".
 */
export function fetchVentasPeriodo(
  desde: string,
  hasta: string,
  agrupacion: string
) {
  return apiFetch<VentasPeriodoItem[]>(
    `/estadisticas/ventas-periodo?desde=${encodeURIComponent(desde)}&hasta=${encodeURIComponent(hasta)}&agrupacion=${encodeURIComponent(agrupacion)}`
  );
}

/**
 * Fetches the top N products by total revenue.
 * Revenue is calculated as SUM(subtotal_snap) across non-cancelled orders.
 *
 * @param limit - Maximum number of products to return (default: 10).
 */
export function fetchProductosTop(limit: number = 10) {
  return apiFetch<ProductoTopItem[]>(
    `/estadisticas/productos-top?limit=${encodeURIComponent(limit)}`
  );
}

/**
 * Fetches the count of non-deleted orders grouped by their estado_codigo.
 */
export function fetchPedidosEstado() {
  return apiFetch<PedidosEstadoItem[]>("/estadisticas/pedidos-estado");
}

/**
 * Fetches revenue grouped by payment method for a date range.
 * Only includes orders that have at least one approved payment.
 *
 * @param desde - Start date as YYYY-MM-DD string (inclusive).
 * @param hasta - End date as YYYY-MM-DD string (inclusive).
 */
export function fetchIngresosFormaPago(desde: string, hasta: string) {
  return apiFetch<IngresosResponse[]>(
    `/estadisticas/ingresos-forma-pago?desde=${encodeURIComponent(desde)}&hasta=${encodeURIComponent(hasta)}`
  );
}
