/**
 * Order (Pedido) API functions.
 *
 * Orders go through a state machine managed by the backend. The relevant
 * transitions are:
 *   - avanzar(id)  → moves the order to the next state (e.g., pendiente → confirmado)
 *   - cancelar(id) → moves the order to a cancelled/final state
 *   - crear(...)   → creates a new order with product snapshots and pricing
 *
 * Each order line item (DetallePedido) stores a snapshot of the product name
 * and price at the time of ordering, so historical data remains accurate even
 * if the product catalog changes later.
 *
 * Stock validation can be performed before order creation via validarStock(),
 * which checks product availability without persisting anything.
 */
import { apiFetch } from "./client";

// ── Types ──

/**
 * A single line item within an order.
 * `nombre_snapshot`, `precio_snapshot`, and `subtotal_snap` are frozen at
 * order creation time to preserve historical accuracy.
 */
export interface DetallePedido {
  producto_id: number;
  cantidad: number;
  nombre_snapshot: string;
  precio_snapshot: string;
  subtotal_snap: string;
  personalizacion?: number[] | null;
}

/** Minimal user info embedded in order responses for display purposes. */
export interface UsuarioInfo {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
}

/**
 * Full order entity returned by the API.
 * Contains pricing breakdown (subtotal, discount, shipping, total) as strings
 * to avoid floating-point precision issues.
 */
export interface Pedido {
  id: number;
  usuario_id: number;
  direccion_id: number | null;
  estado_codigo: string;
  forma_pago_codigo: string;
  subtotal: string;
  descuento: string;
  costo_envio: string;
  total: string;
  notas: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  detalles?: DetallePedido[];
  usuario?: UsuarioInfo | null;
}

/** Response from the avanzar endpoint, describing the state transition. */
export interface AvanzarResponse {
  id: number;
  estado_anterior: string;
  estado_actual: string;
  mensaje: string;
}

/** Response from the cancelar endpoint, describing the state transition. */
export interface CancelarResponse {
  id: number;
  estado_anterior: string;
  estado_actual: string;
  mensaje: string;
}

/** Detail about a product whose stock is insufficient to fulfill the order. */
export interface StockInsuficienteDetalle {
  producto_id: number;
  nombre_producto: string;
  cantidad_solicitada: number;
  stock_disponible: number;
}

/** Error payload returned when stock validation fails. */
export interface StockInsuficienteError {
  error: string;
  mensaje: string;
  detalles: StockInsuficienteDetalle[];
}

/** Input item for stock validation. */
export interface ValidarStockDetalleInput {
  producto_id: number;
  cantidad: number;
}

export interface ValidarStockInput {
  detalles: ValidarStockDetalleInput[];
}

/** Result of a stock validation check. */
export interface ValidarStockDetalle {
  producto_id: number;
  nombre_producto: string;
  cantidad_solicitada: number;
  stock_disponible: number;
}

export interface ValidarStockResponse {
  valido: boolean;
  detalles: ValidarStockDetalle[];
}

/** Input for creating a new order. */
export interface CreatePedidoInput {
  usuario_id?: number;
  direccion_id?: number;
  forma_pago_codigo: string;
  subtotal: number;
  descuento?: number;
  costo_envio?: number;
  notas?: string;
  detalles: {
    producto_id: number;
    cantidad: number;
    nombre_snapshot: string;
    precio_snapshot: number;
    personalizacion?: number[];
  }[];
}

export const pedidosApi = {
  /**
   * Fetches orders that are still active (in progress, not yet delivered
   * or cancelled). Used by staff to view current order queues.
   */
  getActivos: (skip = 0, limit = 100) =>
    apiFetch<Pedido[]>(`/pedidos/activos?skip=${skip}&limit=${limit}`),

  /**
   * Fetches completed/cancelled orders (history). Used by staff to review
   * past orders.
   */
  getHistorial: (skip = 0, limit = 100) =>
    apiFetch<Pedido[]>(`/pedidos/historial?skip=${skip}&limit=${limit}`),

  /**
   * Fetches the current user's own orders. Scoped to the authenticated user
   * on the backend.
   */
  getMisPedidos: (skip = 0, limit = 100) =>
    apiFetch<Pedido[]>(`/pedidos/mis-pedidos?skip=${skip}&limit=${limit}`),

  /** Fetches a single order by ID (includes detalles and usuario). */
  getById: (id: number) =>
    apiFetch<Pedido>(`/pedidos/${id}`),

  /**
   * Creates a new order.
   * The backend validates stock, applies pricing, and returns the persisted
   * order entity. Product snapshots are recorded at creation time.
   */
  create: (data: CreatePedidoInput) =>
    apiFetch<Pedido>("/pedidos/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * Advances the order to the next state in the workflow.
   * (e.g., from "pendiente" to "confirmado", or "preparando" to "enviado").
   * The exact transition is defined by the backend state machine.
   */
  avanzar: (id: number) =>
    apiFetch<AvanzarResponse>(`/pedidos/${id}/avanzar`, {
      method: "POST",
    }),

  /**
   * Cancels an order. The backend determines whether cancellation is allowed
   * based on the current state (e.g., already-delivered orders may not be
   * cancellable).
   */
  cancelar: (id: number) =>
    apiFetch<CancelarResponse>(`/pedidos/${id}/cancelar`, {
      method: "POST",
    }),

  /**
   * Updates the quantity of a specific product within an existing order.
   * Used for mid-order adjustments (subject to backend permission checks).
   */
  actualizarDetalle: (pedidoId: number, productoId: number, cantidad: number) =>
    apiFetch<Pedido>(`/pedidos/${pedidoId}/detalles/${productoId}`, {
      method: "PATCH",
      body: JSON.stringify({ cantidad }),
    }),

  /**
   * Validates product stock availability without creating an order.
   * Useful for pre-checking cart contents before the user confirms.
   * The response indicates whether all items have sufficient stock and
   * provides details for any that don't.
   */
  validarStock: (data: ValidarStockInput) =>
    apiFetch<ValidarStockResponse>("/pedidos/validar-stock", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};
