/**
 * Payment (Pago) API functions.
 *
 * MercadoPago payments are initiated when an order transitions to CONFIRMADO
 * and the selected payment method is MERCADOPAGO. The frontend can:
 *   - Initiate a payment (initPayment) to get the payment link.
 *   - Fetch payments for an order (getPagosByPedido) to display status.
 *
 * The actual MercadoPago checkout redirect URL will be implemented in a
 * future integration; currently the backend returns a placeholder.
 */
import { apiFetch } from "./client";

// ── Types ──

/** Full payment record returned by the backend. */
export interface PagoRead {
  id: number;
  pedido_id: number;
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

/** Response from the payment initiation endpoint. */
export interface InitPaymentResponse {
  pago: PagoRead;
  init_point: string;
}

export const pagosApi = {
  /**
   * Initiates a MercadoPago payment for an order.
   * Creates a Pago record with pending status and returns the payment info.
   */
  initPayment: (pedidoId: number) =>
    apiFetch<InitPaymentResponse>("/pagos/", {
      method: "POST",
      body: JSON.stringify({ pedido_id: pedidoId }),
    }),

  /**
   * Lists all payments for a given order.
   * Visible only to ADMIN/PEDIDOS roles.
   */
  getPagosByPedido: (pedidoId: number) =>
    apiFetch<PagoRead[]>(`/pagos/${pedidoId}`),
};
