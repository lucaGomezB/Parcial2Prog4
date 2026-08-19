/**
 * FormaPago API functions.
 *
 * Payment methods are seeded in the database and managed by admins.
 * CLIENT users receive only habilitado=True methods.
 */
import { apiFetch } from "@/shared/api/client";

// ── Types ──

/** Public shape of a payment method returned by GET /formas-pago/. */
export interface FormaPagoPublic {
  codigo: string;
  descripcion: string;
  habilitado: boolean;
}

// ── API ──

export const formasPagoApi = {
  /** Fetch all payment methods visible to the authenticated user. */
  getAll: () => apiFetch<FormaPagoPublic[]>("/formas-pago/"),
};
