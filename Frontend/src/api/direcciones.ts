/**
 * Address (Direccion de entrega) API functions.
 *
 * Each user can have multiple delivery addresses, with one marked as primary.
 * The `setPrincipal` endpoint allows changing the primary address, which is
 * used as the default for new orders.
 */
import { apiFetch } from "./client";

// ── Types ──

export interface DireccionEntrega {
  id: number;
  usuario_id: number;
  alias: string | null;
  linea1: string;
  linea2: string | null;
  ciudad: string;
  provincia: string | null;
  codigo_postal: string | null;
  latitud: string | null;
  longitud: string | null;
  es_principal: boolean;
  created_at: string;
  updated_at: string;
}

export interface DireccionEntregaInput {
  alias?: string | null;
  linea1: string;
  linea2?: string | null;
  ciudad: string;
  provincia?: string | null;
  codigo_postal?: string | null;
  latitud?: string | null;
  longitud?: string | null;
  es_principal?: boolean;
}

export interface DireccionEntregaUpdate {
  alias?: string | null;
  linea1?: string;
  linea2?: string | null;
  ciudad?: string;
  provincia?: string | null;
  codigo_postal?: string | null;
  latitud?: string | null;
  longitud?: string | null;
  es_principal?: boolean;
}

/**
 * Formats a delivery address into a human-readable string.
 * Pattern: "Alias — Street 123, City"
 */
export function formatDireccion(d: DireccionEntrega): string {
  const base = d.alias ? `${d.alias} — ${d.linea1}` : d.linea1;
  return `${base}, ${d.ciudad}`;
}

export const direccionesApi = {
  /** Fetches all addresses for the current user (scoped by the JWT). */
  getAll: () => apiFetch<DireccionEntrega[]>("/direcciones/"),

  /** Fetches a single address by its ID. */
  getById: (id: number) => apiFetch<DireccionEntrega>(`/direcciones/${id}`),

  /** Creates a new delivery address for the current user. */
  create: (data: DireccionEntregaInput) =>
    apiFetch<DireccionEntrega>("/direcciones/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Partially updates an existing address. */
  update: (id: number, data: DireccionEntregaUpdate) =>
    apiFetch<DireccionEntrega>(`/direcciones/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** Deletes an address by its ID. */
  delete: (id: number) =>
    apiFetch<void>(`/direcciones/${id}`, {
      method: "DELETE",
    }),

  /**
   * Marks an address as the primary/default delivery address.
   * The backend handles unmarking the previous primary address.
   */
  setPrincipal: (id: number) =>
    apiFetch<DireccionEntrega>(`/direcciones/${id}/principal`, {
      method: "PATCH",
    }),
};
