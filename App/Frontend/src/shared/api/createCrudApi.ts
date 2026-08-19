/**
 * createCrudApi — CRUD API factory.
 *
 * Creates a standard set of CRUD methods for a given API endpoint,
 * eliminating the duplicated getAll/getById/create/update/delete pattern
 * present across all feature API modules.
 *
 * The returned object is designed to be used with the spread operator
 * so feature modules can add custom methods alongside the standard ones:
 *
 *   export const productosApi = {
 *     ...createCrudApi<Producto>("/productos"),
 *     getIngredientes: (id: number) => ...,
 *   };
 *
 * @typeParam T - The entity type. Must have an `id` field.
 * @param endpoint - API path prefix (e.g., "/productos").
 * @returns An object with getAll, getById, create, update, and delete methods.
 */
import { apiFetch, apiFetchPaginated } from "@/shared/api/client";

export interface CrudApi<T extends { id: number | string }> {
  /** Fetches a paginated list of entities. */
  getAll: (skip?: number, limit?: number) => Promise<T[]>;
  /** Fetches a single entity by ID. */
  getById: (id: number) => Promise<T>;
  /** Creates a new entity. */
  create: (data: Partial<T>) => Promise<T>;
  /** Partially updates an existing entity (PATCH semantics). */
  update: (id: number, data: Partial<T>) => Promise<T>;
  /** Deletes an entity by ID. */
  delete: (id: number) => Promise<void>;
}

export function createCrudApi<T extends { id: number | string }>(endpoint: string): CrudApi<T> {
  return {
    getAll: (skip = 0, limit = 100) =>
      apiFetchPaginated<T>(`${endpoint}/?skip=${skip}&limit=${limit}`),

    getById: (id: number) =>
      apiFetch<T>(`${endpoint}/${id}`),

    create: (data: Partial<T>) =>
      apiFetch<T>(`${endpoint}/`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (id: number, data: Partial<T>) =>
      apiFetch<T>(`${endpoint}/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    delete: (id: number) =>
      apiFetch<void>(`${endpoint}/${id}`, { method: "DELETE" }),
  };
}
