import { apiFetch } from "./client";

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
  getAll: (skip = 0, limit = 100) =>
    apiFetch<Categoria[]>(`/categorias/?skip=${skip}&limit=${limit}`),

  getById: (id: number) => apiFetch<Categoria>(`/categorias/${id}`),

  getTree: () => apiFetch<CategoriaTree[]>("/categorias/tree"),

  create: (data: CategoriaCreate) =>
    apiFetch<Categoria>("/categorias/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: number, data: CategoriaUpdate) =>
    apiFetch<Categoria>(`/categorias/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    apiFetch<void>(`/categorias/${id}`, { method: "DELETE" }),
};
