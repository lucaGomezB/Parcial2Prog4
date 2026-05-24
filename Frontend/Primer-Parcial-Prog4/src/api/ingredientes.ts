import { apiFetch } from "./client";

export interface Ingrediente {
  id: number;
  nombre: string;
  es_alergeno: boolean;
}

export interface IngredienteCreate {
  nombre: string;
  es_alergeno?: boolean;
}

export interface IngredienteUpdate {
  nombre?: string | null;
  es_alergeno?: boolean | null;
}

export const ingredientesApi = {
  getAll: (skip = 0, limit = 100) =>
    apiFetch<Ingrediente[]>(`/ingredientes/?skip=${skip}&limit=${limit}`),

  getById: (id: number) => apiFetch<Ingrediente>(`/ingredientes/${id}`),

  create: (data: IngredienteCreate) =>
    apiFetch<Ingrediente>("/ingredientes/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: number, data: IngredienteUpdate) =>
    apiFetch<Ingrediente>(`/ingredientes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    apiFetch<void>(`/ingredientes/${id}`, { method: "DELETE" }),
};
