/**
 * User (admin) API functions.
 *
 * These endpoints are used for user management by administrators.
 * They support CRUD operations on user accounts and role assignment.
 * The `getAll` endpoint optionally filters by role code.
 *
 * Note: Regular user registration (self-service signup) is handled by a
 * different endpoint (/auth/register) not defined in this module.
 */
import { apiFetch } from "./client";

// ── Types ──

export interface RolSimple {
  codigo: string;
  nombre: string;
}

export interface Usuario {
  id: number;
  nombre: string;
  apellido: string;
  email: string;
  celular: string | null;
  roles: RolSimple[];
}

export interface UsuarioCreate {
  nombre: string;
  apellido: string;
  email: string;
  celular?: string | null;
  password: string;
  roles_codigos?: string[];
}

export interface UsuarioUpdate {
  nombre?: string;
  apellido?: string;
  email?: string;
  celular?: string | null;
  roles_codigos?: string[];
}

export const usuariosApi = {
  /** Creates a new user with the given profile data and optional role assignments. */
  create: (data: UsuarioCreate) =>
    apiFetch<Usuario>("/usuarios/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /**
   * Fetches a paginated list of users.
   * Optionally filters by role code (e.g., "ADMIN", "CLIENTE").
   */
  getAll: (skip = 0, limit = 100, rolCodigo?: string) => {
    let url = `/usuarios/?skip=${skip}&limit=${limit}`;
    if (rolCodigo) url += `&rol_codigo=${rolCodigo}`;
    return apiFetch<Usuario[]>(url);
  },

  /** Fetches a single user by ID. */
  getById: (id: number) =>
    apiFetch<Usuario>(`/usuarios/${id}`),

  /** Partially updates a user's profile and/or role assignments. */
  update: (id: number, data: UsuarioUpdate) =>
    apiFetch<Usuario>(`/usuarios/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  /** Deletes a user account by ID. */
  delete: (id: number) =>
    apiFetch<void>(`/usuarios/${id}`, {
      method: "DELETE",
    }),
};
