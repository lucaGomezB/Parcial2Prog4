import { apiFetch } from "./client";

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

export interface UsuarioUpdate {
  nombre?: string;
  apellido?: string;
  email?: string;
  celular?: string | null;
  roles_codigos?: string[];
}

export const usuariosApi = {
  getAll: (skip = 0, limit = 100, rolCodigo?: string) => {
    let url = `/usuarios/?skip=${skip}&limit=${limit}`;
    if (rolCodigo) url += `&rol_codigo=${rolCodigo}`;
    return apiFetch<Usuario[]>(url);
  },

  getById: (id: number) =>
    apiFetch<Usuario>(`/usuarios/${id}`),

  update: (id: number, data: UsuarioUpdate) =>
    apiFetch<Usuario>(`/usuarios/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  delete: (id: number) =>
    apiFetch<void>(`/usuarios/${id}`, {
      method: "DELETE",
    }),
};
