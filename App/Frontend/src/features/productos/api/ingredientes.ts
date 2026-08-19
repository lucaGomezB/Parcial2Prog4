/**
 * Ingredient API functions.
 *
 * Ingredients represent the raw components used in products (e.g., flour, cheese).
 * They track allergen information, current price, and stock levels independently
 * of products.
 */
import { createCrudApi } from "@/shared/api/createCrudApi";
import { apiFetch } from "@/shared/api/client";

// ── Types ──

export interface Ingrediente {
  id: number;
  nombre: string;
  descripcion?: string | null;
  es_alergeno: boolean;
  precio_actual: number;
  stock_actual: number;
  unidad_medida_id?: number | null;
  unidad_medida_simbolo?: string | null;
}

export interface IngredienteCreate {
  nombre: string;
  descripcion?: string | null;
  es_alergeno?: boolean;
  precio_actual?: number;
  stock_actual?: number;
  unidad_medida_id?: number | null;
}

export interface IngredienteUpdate {
  nombre?: string | null;
  descripcion?: string | null;
  es_alergeno?: boolean | null;
  precio_actual?: number | null;
  stock_actual?: number | null;
  unidad_medida_id?: number | null;
}

/** Product affected by an ingredient's stock level. Used to show which
 * products depend on a given ingredient and their derived stock values. */
export interface AfectadoProducto {
  id: number;
  nombre: string;
  stock_derivado: number;
  es_producto_terminado: boolean;
  stock_manual?: number | null;
}

export const ingredientesApi = {
  ...createCrudApi<Ingrediente>("/ingredientes"),

  /** Returns products that use this ingredient, with their derived stock values. */
  getProductosAfectados: (ingredienteId: number) =>
    apiFetch<AfectadoProducto[]>(`/ingredientes/${ingredienteId}/productos`),
};
