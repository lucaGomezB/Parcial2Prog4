import { apiFetch } from "./client";

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
}

/** Formatea una dirección para mostrar: "Alias — Calle 123, Ciudad" */
export function formatDireccion(d: DireccionEntrega): string {
  const base = d.alias ? `${d.alias} — ${d.linea1}` : d.linea1;
  return `${base}, ${d.ciudad}`;
}

export const direccionesApi = {
  getAll: () => apiFetch<DireccionEntrega[]>("/direcciones/"),

  getById: (id: number) => apiFetch<DireccionEntrega>(`/direcciones/${id}`),

  create: (data: DireccionEntregaInput) =>
    apiFetch<DireccionEntrega>("/direcciones/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: number, data: DireccionEntregaUpdate) =>
    apiFetch<DireccionEntrega>(`/direcciones/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    apiFetch<void>(`/direcciones/${id}`, {
      method: "DELETE",
    }),

  setPrincipal: (id: number) =>
    apiFetch<DireccionEntrega>(`/direcciones/${id}/principal`, {
      method: "PATCH",
    }),
};
