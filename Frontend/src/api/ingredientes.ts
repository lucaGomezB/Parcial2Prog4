/**
 * Ingredient API functions.
 *
 * Ingredients represent the raw components used in products (e.g., flour, cheese).
 * They track allergen information, current price, and stock levels independently
 * of products. The `updatePrecio` and `updateStock` endpoints allow partial
 * updates specific to pricing and inventory operations.
 */
import { apiFetch } from "./client";

// ── Types ──

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
  /** Fetches a paginated list of all ingredients. */
  getAll: (skip = 0, limit = 100) =>
    apiFetch<Ingrediente[]>(`/ingredientes/?skip=${skip}&limit=${limit}`),

  /** Fetches a single ingredient by ID. */
  getById: (id: number) => apiFetch<Ingrediente>(`/ingredientes/${id}`),

  /** Creates a new ingredient. */
  create: (data: IngredienteCreate) =>
    apiFetch<Ingrediente>("/ingredientes/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Partially updates an existing ingredient. */
  update: (id: number, data: IngredienteUpdate) =>
    apiFetch<Ingrediente>(`/ingredientes/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** Deletes an ingredient by ID. */
  delete: (id: number) =>
    apiFetch<void>(`/ingredientes/${id}`, { method: "DELETE" }),

  /**
   * Updates only the price of an ingredient.
   * Separate from the general update to allow granular permission checks
   * and price-specific audit logging on the backend.
   */
  updatePrecio: (id: number, precio: number) =>
    apiFetch<Ingrediente>(`/ingredientes/${id}/precio`, {
      method: "PATCH",
      body: JSON.stringify({ precio }),
    }),

  /**
   * Updates only the stock quantity of an ingredient.
   * Separate endpoint to support stock-specific workflows (e.g., inventory
   * adjustments without changing price or other fields).
   */
  updateStock: (id: number, stock: number) =>
    apiFetch<Ingrediente>(`/ingredientes/${id}/stock`, {
      method: "PATCH",
      body: JSON.stringify({ stock }),
    }),
};
