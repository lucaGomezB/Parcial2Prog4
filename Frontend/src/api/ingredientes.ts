import { apiFetch } from "./client";

export interface Ingrediente {
  id: number;
  nombre: string;
  es_alergeno: boolean;
  precio_actual: number;
  stock_actual: number;
}

export interface IngredienteCreate {
  nombre: string;
  es_alergeno?: boolean;
  precio_actual?: number;
  stock_actual?: number;
}

export interface IngredienteUpdate {
  nombre?: string | null;
  es_alergeno?: boolean | null;
  precio_actual?: number | null;
  stock_actual?: number | null;
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

  updatePrecio: (id: number, precio: number) =>
    apiFetch<Ingrediente>(`/ingredientes/${id}/precio`, {
      method: "PATCH",
      body: JSON.stringify({ precio }),
    }),

  updateStock: (id: number, stock: number) =>
    apiFetch<Ingrediente>(`/ingredientes/${id}/stock`, {
      method: "PATCH",
      body: JSON.stringify({ stock }),
    }),
};
