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
import { apiFetch } from "./client";

// ── Types ──

export interface Producto {
  id: number;
  nombre: string;
  descripcion: string | null;
  receta?: string | null;
  precio_base: number;
  imagenes_url: string[];
  stock_cantidad: number;
  tiempo_prep_min: number;
  disponible: boolean;
  tiene_ingredientes?: boolean;
}

export interface IngredienteAsignado {
  ingrediente_id: number;
  cantidad?: number;
  es_removible?: boolean;
  es_principal?: boolean;
  orden?: number;
}

export interface ProductoCreate {
  nombre: string;
  descripcion?: string | null;
  receta?: string | null;
  precio_base?: number;
  stock_cantidad?: number;
  imagenes_url?: string[];
  tiempo_prep_min?: number;
  disponible?: boolean;
  categorias_ids?: number[];
  categoria_principal_id?: number | null;
  ingredientes?: IngredienteAsignado[];
}

export interface ProductoUpdate {
  nombre?: string | null;
  descripcion?: string | null;
  receta?: string | null;
  precio_base?: number | null;
  stock_cantidad?: number | null;
  disponible?: boolean | null;
  categorias_ids?: number[] | null;
}

export interface ProductoIngredienteRead {
  ingrediente_id: number;
  ingrediente_nombre: string;
  es_removible: boolean;
  es_principal: boolean;
  orden: number;
  cantidad: number;
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

export const productosApi = {
  /** Fetches a paginated list of all products. */
  getAll: (skip = 0, limit = 100) =>
    apiFetch<Producto[]>(`/productos/?skip=${skip}&limit=${limit}`),

  /** Fetches a single product by its ID. */
  getById: (id: number) => apiFetch<Producto>(`/productos/${id}`),

  /** Creates a new product with optional category and ingredient assignments. */
  create: (data: ProductoCreate) =>
    apiFetch<Producto>("/productos/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Partially updates an existing product (PATCH semantics). */
  update: (id: number, data: ProductoUpdate) =>
    apiFetch<Producto>(`/productos/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** Deletes a product by its ID. */
  delete: (id: number) =>
    apiFetch<void>(`/productos/${id}`, { method: "DELETE" }),

  // Relaciones Producto-Ingrediente

  /** Fetches all ingredients assigned to a product. */
  getIngredientes: (productoId: number) =>
    apiFetch<ProductoIngredienteRead[]>(`/productos/${productoId}/ingredientes`),

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

  /** Updates the quantity of an assigned ingredient for a product. */
  updateIngredienteCantidad: (productoId: number, ingredienteId: number, cantidad: number) =>
    apiFetch<ProductoIngredienteRead[]>(`/productos/${productoId}/ingredientes/${ingredienteId}`, {
      method: "PATCH",
      body: JSON.stringify({ cantidad }),
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
