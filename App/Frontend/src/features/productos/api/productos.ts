/**
 * Product API functions.
 *
 * All functions delegate to the shared `apiFetch` wrapper which handles
 * authentication headers, JSON serialization, and error propagation.
 *
 * Error handling convention: callers are expected to wrap these calls in
 * try/catch blocks. The axios response interceptor in client.ts already
 * handles 401 (auto-refresh) and network-level errors. Any other HTTP error
 * status is thrown as an AxiosError for the caller to handle.
 */
import { apiFetch } from "@/shared/api/client";
import { createCrudApi } from "@/shared/api/createCrudApi";

// ── Types ──

export interface Producto {
  id: number;
  nombre: string;
  descripcion: string | null;
  receta?: string | null;
  precio_base: number;
  precio_actual: number;
  imagenes_url: string[];
  stock_cantidad: number;
  tiempo_prep_min: number;
  disponible: boolean;
  es_producto_terminado: boolean;
  tiene_ingredientes?: boolean;
  categoria_ids: number[];
  unidad_medida_id?: number | null;
  unidad_medida_simbolo?: string | null;
}

export interface IngredienteAsignado {
  ingrediente_id: number;
  cantidad?: number;
  es_removible?: boolean;
  es_principal?: boolean;
  orden?: number;
  unidad_medida_id?: number | null;
}

export interface ProductoCreate {
  nombre: string;
  descripcion?: string | null;
  receta?: string | null;
  precio_base?: number;
  precio_actual?: number;
  imagenes_url?: string[];
  tiempo_prep_min?: number;
  disponible?: boolean;
  es_producto_terminado?: boolean;
  categorias_ids?: number[];
  categoria_principal_id?: number | null;
  ingredientes?: IngredienteAsignado[];
  unidad_medida_id?: number | null;
}

/** Form-local type that extends ProductoCreate with stock_cantidad for UI use.
 * stock_cantidad is NOT sent to the backend for regular products (it's derived
 * from ingredient stock). For es_producto_terminado products, the field is
 * displayed but not persisted via this schema. */
export type ProductoFormValues = ProductoCreate & { stock_cantidad?: number; };

export interface ProductoUpdate {
  nombre?: string | null;
  descripcion?: string | null;
  receta?: string | null;
  precio_base?: number | null;
  precio_actual?: number | null;
  imagenes_url?: string[];
  disponible?: boolean | null;
  es_producto_terminado?: boolean | null;
  categorias_ids?: number[] | null;
  unidad_medida_id?: number | null;
  ingredientes?: IngredienteAsignado[];
}

export interface ProductoIngredienteRead {
  ingrediente_id: number;
  ingrediente_nombre: string;
  es_removible: boolean;
  es_principal: boolean;
  orden: number;
  cantidad: number;
  es_alergeno: boolean;
  unidad_medida_id?: number | null;
  unidad_medida_simbolo?: string | null;
}

export interface ProductoCategoriaRead {
  categoria_id: number;
  categoria_nombre: string;
  es_principal: boolean;
}

export interface CategoriaAsignada {
  categoria_id: number;
  es_principal?: boolean;
}

export interface IngredienteStockDetail {
  ingrediente_id: number;
  ingrediente_nombre: string;
  stock_actual: number;
  cantidad_receta: number;
  cantidad_convertida: number;
  unidad_medida_simbolo: string | null;
  producible: number;
  es_limitante: boolean;
  deficit: number;
}

export interface ProductoIngredientesCompartidos {
  producto_id: number;
  ingredientes: string[];
}

export const productosApi = {
  ...createCrudApi<Producto>("/productos"),

  // Relaciones Producto-Ingrediente

  /** Fetches all ingredients assigned to a product. */
  getIngredientes: (productoId: number) =>
    apiFetch<ProductoIngredienteRead[]>(`/productos/${productoId}/ingredientes`),

  /** Fetches per-ingredient stock breakdown showing limiting factors. */
  getIngredientesStockDetail: (productoId: number) =>
    apiFetch<IngredienteStockDetail[]>(`/productos/${productoId}/ingredientes-stock`),

  /** Fetches the map of products to the ingredient names they share with other products. */
  getIngredientesCompartidos: () =>
    apiFetch<ProductoIngredientesCompartidos[]>("/productos/ingredientes-compartidos"),

  /** Assigns an ingredient to a product with optional metadata (removable, main, etc.). */
  addIngrediente: (productoId: number, data: IngredienteAsignado) =>
    apiFetch<ProductoIngredienteRead[]>(`/productos/${productoId}/ingredientes`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Removes an ingredient assignment from a product. */
  removeIngrediente: (productoId: number, ingredienteId: number) =>
    apiFetch<void>(`/productos/${productoId}/ingredientes/${ingredienteId}`, {
      method: "DELETE",
    }),

  /** Updates the quantity (and optionally unit) of an assigned ingredient for a product. */
  updateIngredienteCantidad: (productoId: number, ingredienteId: number, cantidad: number, unidad_medida_id?: number | null) =>
    apiFetch<ProductoIngredienteRead[]>(`/productos/${productoId}/ingredientes/${ingredienteId}`, {
      method: "PATCH",
      body: JSON.stringify({ cantidad, ...(unidad_medida_id !== undefined ? { unidad_medida_id } : {}) }),
    }),

  /** Toggles a boolean field (es_removible, es_principal) on an ingredient assignment, preserving current cantidad. */
  toggleIngredienteFlag: (productoId: number, ingredienteId: number, field: "es_removible" | "es_principal", value: boolean, cantidad: number) =>
    apiFetch<ProductoIngredienteRead[]>(`/productos/${productoId}/ingredientes/${ingredienteId}`, {
      method: "PATCH",
      body: JSON.stringify({ [field]: value, cantidad }),
    }),

  // Relaciones Producto-Categoria

  /** Fetches all category assignments for a product. */
  getCategorias: (productoId: number) =>
    apiFetch<ProductoCategoriaRead[]>(`/productos/${productoId}/categorias`),

  /** Assigns a category to a product (optionally as the main category). */
  addCategoria: (productoId: number, data: CategoriaAsignada) =>
    apiFetch<ProductoCategoriaRead[]>(`/productos/${productoId}/categorias`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Removes a category assignment from a product. */
  removeCategoria: (productoId: number, categoriaId: number) =>
    apiFetch<void>(`/productos/${productoId}/categorias/${categoriaId}`, {
      method: "DELETE",
    }),
};
