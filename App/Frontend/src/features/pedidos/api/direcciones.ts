/**
 * Address (Direccion de entrega) API functions.
 *
 * Each user can have multiple delivery addresses, with one marked as primary.
 * The `setPrincipal` endpoint allows changing the primary address, which is
 * used as the default for new orders.
 */
import { apiFetch } from "@/shared/api/client";
import { createCrudApi } from "@/shared/api/createCrudApi";

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
  es_local: boolean;
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
  es_local?: boolean;
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
  es_local?: boolean;
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
  ...createCrudApi<DireccionEntrega>("/direcciones"),

  /**
   * Fetches all addresses for the current user (scoped by the JWT).
   * Overrides the default paginated getAll with a non-paginated version.
   * When incluirLocales=true, also returns company stores (es_local=True)
   * for pickup location selection.
   */
  getAll: (incluirLocales = false) => {
    const url = incluirLocales ? "/direcciones/?incluir_locales=true" : "/direcciones/";
    return apiFetch<DireccionEntrega[]>(url);
  },

  /**
   * Marks an address as the primary/default delivery address.
   * The backend handles unmarking the previous primary address.
   */
  setPrincipal: (id: number) =>
    apiFetch<DireccionEntrega>(`/direcciones/${id}/principal`, {
      method: "PATCH",
    }),
};
