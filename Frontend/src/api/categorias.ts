/**
 * Category API functions.
 *
 * Categories form a hierarchical tree structure (parent/child), used to
 * organize products. The `getTree()` endpoint returns the full hierarchy
 * in a single request.
 */
import { apiFetch } from "./client";

// ── Types ──

export interface Categoria {
  id: number;
  nombre: string;
  descripcion: string | null;
  parent_id: number | null;
  orden_display: number;
}

export interface CategoriaCreate {
  nombre: string;
  descripcion?: string | null;
  parent_id?: number | null;
  orden_display?: number;
}

export interface CategoriaUpdate {
  nombre?: string | null;
  descripcion?: string | null;
  parent_id?: number | null;
  orden_display?: number | null;
}

/**
 * Recursive tree node returned by getTree().
 * Each node contains an array of its own children (subcategories).
 */
export interface CategoriaTree {
  id: number;
  nombre: string;
  descripcion: string | null;
  parent_id: number | null;
  imagen_url: string | null;
  orden_display: number;
  subcategorias: CategoriaTree[];
}

export const categoriasApi = {
  /** Fetches a flat, paginated list of all categories. */
  getAll: (skip = 0, limit = 100) =>
    apiFetch<Categoria[]>(`/categorias/?skip=${skip}&limit=${limit}`),

  /** Fetches a single category by ID. */
  getById: (id: number) => apiFetch<Categoria>(`/categorias/${id}`),

  /**
   * Fetches the full category tree (hierarchical, with parent/child nesting).
   * This is the primary endpoint for building navigation menus.
   */
  getTree: () => apiFetch<CategoriaTree[]>("/categorias/tree"),

  /** Creates a new category. */
  create: (data: CategoriaCreate) =>
    apiFetch<Categoria>("/categorias/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** Partially updates an existing category. */
  update: (id: number, data: CategoriaUpdate) =>
    apiFetch<Categoria>(`/categorias/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** Deletes a category by ID. */
  delete: (id: number) =>
    apiFetch<void>(`/categorias/${id}`, { method: "DELETE" }),
};
