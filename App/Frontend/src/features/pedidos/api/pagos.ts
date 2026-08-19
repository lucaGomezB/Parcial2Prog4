/**
 * Payment (Pago) API functions.
 *
 * MercadoPago payments are initiated from cart (post-pago flow).
 *
 * Flow:
 *   1. User selects MERCADOPAGO in cart
 *   2. initFromCart() creates Pago + snapshot + MP preference
 *   3. User is redirected to MP (cart preserved)
 *   4. MP webhook creates Pedido from snapshot
 *   5. WebSocket pago_confirmado event clears cart and navigates
 */
import { apiFetch } from "@/shared/api/client";

// ── Types ──

/** Full payment record returned by the backend. */
export interface PagoRead {
  id: number;
  pedido_id: number | null;
  mp_payment_id: number | null;
  mp_status: string;
  mp_status_detail: string | null;
  external_reference: string;
  idempotency_key: string;
  transaction_amount: number;
  payment_method_id: string | null;
  created_at: string;
  updated_at: string;
}

/** A single cart item for init-from-cart. */
export interface CartItem {
  producto_id: number;
  nombre: string;
  precio: number;
  cantidad: number;
  ingredientes_excluidos: number[];
}

/** Request schema: POST /pagos/init-from-cart. */
export interface InitFromCartRequest {
  forma_pago_codigo: string;
  subtotal: number;
  descuento?: number;
  costo_envio?: number;
  direccion_id?: number | null;
  notas?: string | null;
  items: CartItem[];
}

/** Response from the payment initiation endpoint.
 *  init_point is null when MercadoPago API call fails. */
export interface InitPaymentResponse {
  pago: PagoRead;
  init_point: string | null;
  error?: string | null;
}

/** Response from the payment status polling endpoint. */
export interface PaymentStatusResponse {
  status: "found" | "pending" | "not_found" | "error";
  pedido_id: number | null;
  mp_status: string | null;
  error?: string | null;
}

export const pagosApi = {
  /**
   * Initiates a MercadoPago payment from cart items (POST /pagos/init-from-cart).
   *
   * This is the NEW post-pago flow. Cart is NOT cleared here — it's cleared
   * by the WebSocket pago_confirmado event when payment is confirmed.
   */
  initFromCart: (data: InitFromCartRequest) =>
    apiFetch<InitPaymentResponse>("/pagos/init-from-cart", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * Lists all payments for a given order.
   * Visible only to ADMIN/PEDIDOS roles.
   */
  getPagosByPedido: (pedidoId: number) =>
    apiFetch<PagoRead[]>(`/pagos/${pedidoId}`),

  /**
   * Polls for Pedido creation after MercadoPago payment.
   * Returns found, pending, or not_found with pedido_id when available.
   */
  getPaymentStatus: (externalReference: string) =>
    apiFetch<PaymentStatusResponse>(`/pagos/status?external_reference=${externalReference}`),
};
