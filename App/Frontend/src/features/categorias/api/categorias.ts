/**
 * Category API functions.
 *
 * Categories form a hierarchical tree structure (parent/child), used to
 * organize products. The `getTree()` endpoint returns the full hierarchy
 * in a single request.
 */
import { apiFetch } from "@/shared/api/client";
import { createCrudApi } from "@/shared/api/createCrudApi";

// ── Types ──

export interface Categoria {
  id: number;
  nombre: string;
  descripcion: string | null;
  parent_id: number | null;
  imagen_url: string[];
  orden_display: number;
}

export interface CategoriaCreate {
  nombre: string;
  descripcion?: string | null;
  parent_id?: number | null;
  imagenes_url?: string[];
  orden_display?: number;
}

export interface CategoriaUpdate {
  nombre?: string | null;
  descripcion?: string | null;
  parent_id?: number | null;
  imagenes_url?: string[];
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
  imagen_url: string[];
  orden_display: number;
  subcategorias: CategoriaTree[];
}

export const categoriasApi = {
  ...createCrudApi<Categoria>("/categorias"),

  /**
   * Fetches the full category tree (hierarchical, with parent/child nesting).
   * This is the primary endpoint for building navigation menus.
   */
  getTree: () => apiFetch<CategoriaTree[]>("/categorias/tree"),
};
