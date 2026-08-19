/**
 * UnidadMedida API functions.
 *
 * All functions delegate to the shared apiFetch wrapper which handles
 * authentication headers, JSON serialization, and error propagation.
 *
 * Endpoint: /api/v1/unidades-medida/
 */
import { apiFetch } from "@/shared/api/client";
import { createCrudApi } from "@/shared/api/createCrudApi";
import type { UnidadMedida, UnidadMedidaCreate, UnidadMedidaUpdate } from "@/features/unidades-medida/types";

export type { UnidadMedida };

const baseCrud = createCrudApi<UnidadMedida>("/unidades-medida");

export const unidadesMedidaApi = {
  /** Fetches all measurement units, optionally filtered by tipo. */
  getAll: (tipo?: string) =>
    apiFetch<UnidadMedida[]>(
      `/unidades-medida/${tipo ? `?tipo=${tipo}` : ""}`,
    ),

  /** Fetches a single measurement unit by ID. */
  getById: baseCrud.getById,

  /** Creates a new measurement unit. ADMIN only. */
  create: (data: UnidadMedidaCreate) =>
    apiFetch<UnidadMedida>("/unidades-medida/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Updates an existing measurement unit by ID. ADMIN only. */
  update: (id: number, data: UnidadMedidaUpdate) =>
    apiFetch<UnidadMedida>(`/unidades-medida/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  /** Deletes a measurement unit by ID. ADMIN only. */
  remove: (id: number) =>
    apiFetch<void>(`/unidades-medida/${id}`, { method: "DELETE" }),
};
