import { apiFetch } from "./client";

export interface Producto {
  id: number;
  nombre: string;
  descripcion: string | null;
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
  getAll: (skip = 0, limit = 100) =>
    apiFetch<Producto[]>(`/productos/?skip=${skip}&limit=${limit}`),

  getById: (id: number) => apiFetch<Producto>(`/productos/${id}`),

  create: (data: ProductoCreate) =>
    apiFetch<Producto>("/productos/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: number, data: ProductoUpdate) =>
    apiFetch<Producto>(`/productos/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    apiFetch<void>(`/productos/${id}`, { method: "DELETE" }),

  // Relaciones Producto-Ingrediente
  getIngredientes: (productoId: number) =>
    apiFetch<ProductoIngredienteRead[]>(`/productos/${productoId}/ingredientes`),

  addIngrediente: (productoId: number, data: IngredienteAsignado) =>
    apiFetch<ProductoIngredienteRead[]>(`/productos/${productoId}/ingredientes`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  removeIngrediente: (productoId: number, ingredienteId: number) =>
    apiFetch<void>(`/productos/${productoId}/ingredientes/${ingredienteId}`, {
      method: "DELETE",
    }),

  updateIngredienteCantidad: (productoId: number, ingredienteId: number, cantidad: number) =>
    apiFetch<ProductoIngredienteRead[]>(`/productos/${productoId}/ingredientes/${ingredienteId}`, {
      method: "PATCH",
      body: JSON.stringify({ cantidad }),
    }),

  // Relaciones Producto-Categoría
  getCategorias: (productoId: number) =>
    apiFetch<ProductoCategoriaRead[]>(`/productos/${productoId}/categorias`),

  addCategoria: (productoId: number, data: CategoriaAsignada) =>
    apiFetch<ProductoCategoriaRead[]>(`/productos/${productoId}/categorias`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  removeCategoria: (productoId: number, categoriaId: number) =>
    apiFetch<void>(`/productos/${productoId}/categorias/${categoriaId}`, {
      method: "DELETE",
    }),

};
