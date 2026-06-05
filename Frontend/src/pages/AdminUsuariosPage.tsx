/**
 * AdminUsuariosPage — User management admin page (RBAC).
 *
 * Access: ADMIN role only (others are redirected to /productos via a guard effect).
 *
 * Features:
 *   - Paginated list of all users with their assigned roles.
 *   - Create user (with password and role selection).
 *   - Edit user (personal info + role toggles).
 *   - Delete user (ADMIN users cannot be deleted).
 *   - Filter by role.
 *   - Role badges with color coding by role type.
 *
 * State management:
 *   - useState for the data grid, filter, modals.
 *   - TanStack Form for both create and edit modals.
 *   - Roles are fetched from /roles/ once on mount.
 */

import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { usuariosApi, type Usuario, type UsuarioCreate, type UsuarioUpdate } from "../api/usuarios";
import { apiFetch, getUserRoles } from "../api/client";
import { useAppForm, required, email, minLength, composeValidators } from "../hooks/useAppForm";

const PAGE_SIZE = 10;

interface RolOption {
  codigo: string;
  nombre: string;
}

/* ── Modal de edicion ── */

/**
 * Modal for editing an existing user's personal info and roles.
 *
 * The user's current roles are pre-selected. The admin can toggle any role on/off.
 * The form includes: nombre, apellido, email, celular, and roles.
 */
function EditarUsuarioModal({
  usuario,
  todosRoles,
  onClose,
  onSave,
}: {
  usuario: Usuario;
  todosRoles: RolOption[];
  onClose: () => void;
  onSave: (id: number, data: UsuarioUpdate) => Promise<void>;
}) {
  const [rolesSel, setRolesSel] = useState<string[]>(
    usuario.roles.map((r) => r.codigo)
  );
  const [guardando, setGuardando] = useState(false);

  interface EditarForm {
    nombre: string;
    apellido: string;
    email: string;
    celular: string;
  }

  const form = useAppForm<EditarForm>({
    defaultValues: {
      nombre: usuario.nombre,
      apellido: usuario.apellido,
      email: usuario.email,
      celular: usuario.celular ?? "",
    },
    onSubmit: async ({ value }) => {
      setGuardando(true);
      try {
        await onSave(usuario.id, {
          nombre: value.nombre.trim(),
          apellido: value.apellido.trim(),
          email: value.email.trim(),
          celular: value.celular.trim() || null,
          roles_codigos: rolesSel,
        });
        onClose();
      } finally {
        setGuardando(false);
      }
    },
  });

  /** Toggles a role code in/out of the selected set. */
  const toggleRol = (codigo: string) => {
    setRolesSel((prev) =>
      prev.includes(codigo)
        ? prev.filter((c) => c !== codigo)
        : [...prev, codigo]
    );
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded p-6 w-full max-w-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold mb-4">
          Editar Usuario #{usuario.id}
        </h2>
        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="space-y-3">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre
              </label>
              <form.Field
                name="nombre"
                validators={{ onChange: composeValidators(required()) }}
              >
                {(field) => (
                  <input
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                  />
                )}
              </form.Field>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Apellido
              </label>
              <form.Field
                name="apellido"
                validators={{ onChange: composeValidators(required()) }}
              >
                {(field) => (
                  <input
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                  />
                )}
              </form.Field>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <form.Field
              name="email"
              validators={{
                onChange: composeValidators(required(), email()),
              }}
            >
              {(field) => (
                <input
                  type="email"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              )}
            </form.Field>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Celular
            </label>
            <form.Field name="celular">
              {(field) => (
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              )}
            </form.Field>
          </div>
          {/* Role toggle buttons: each role is a pill that can be toggled on/off */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Roles
            </label>
            <div className="flex flex-wrap gap-2">
              {todosRoles.map((rol) => (
                <button
                  key={rol.codigo}
                  type="button"
                  onClick={() => toggleRol(rol.codigo)}
                  className={`px-3 py-1 rounded text-sm border cursor-pointer transition-colors ${
                    rolesSel.includes(rol.codigo)
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                  }`}
                >
                  {rol.nombre}
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-100 cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={guardando}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
            >
              {guardando ? "Guardando..." : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Modal de creacion ── */

/**
 * Modal for creating a new user.
 *
 * Includes password and confirm password fields with client-side validation.
 * Default role: CLIENT (pre-selected). The admin can toggle additional roles.
 */
function CrearUsuarioModal({
  todosRoles,
  onClose,
  onSave,
}: {
  todosRoles: RolOption[];
  onClose: () => void;
  onSave: (data: UsuarioCreate) => Promise<void>;
}) {
  const [rolesSel, setRolesSel] = useState<string[]>(["CLIENT"]);
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  interface CrearForm {
    nombre: string;
    apellido: string;
    email: string;
    celular: string;
    password: string;
    confirmPassword: string;
  }

  const form = useAppForm<CrearForm>({
    defaultValues: {
      nombre: "",
      apellido: "",
      email: "",
      celular: "",
      password: "",
      confirmPassword: "",
    },
    onSubmit: async ({ value }) => {
      setError(null);

      if (value.password.length < 6) {
        setError("La contrasena debe tener al menos 6 caracteres");
        return;
      }
      if (value.password !== value.confirmPassword) {
        setError("Las contrasenas no coinciden");
        return;
      }

      setGuardando(true);
      try {
        await onSave({
          nombre: value.nombre.trim(),
          apellido: value.apellido.trim(),
          email: value.email.trim(),
          celular: value.celular.trim() || null,
          password: value.password,
          roles_codigos: rolesSel,
        });
        onClose();
      } finally {
        setGuardando(false);
      }
    },
  });

  /** Toggles a role code in/out of the selected set. */
  const toggleRol = (codigo: string) => {
    setRolesSel((prev) =>
      prev.includes(codigo)
        ? prev.filter((c) => c !== codigo)
        : [...prev, codigo]
    );
  };

  return (
    <div
      className="fixed inset-0 bg-black/40 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded p-6 w-full max-w-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-bold mb-4">Crear Usuario</h2>
        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="space-y-3">
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-3 py-2 rounded text-sm">
              {error}
            </div>
          )}

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Nombre
              </label>
              <form.Field
                name="nombre"
                validators={{ onChange: composeValidators(required()) }}
              >
                {(field) => (
                  <input
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                  />
                )}
              </form.Field>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Apellido
              </label>
              <form.Field
                name="apellido"
                validators={{ onChange: composeValidators(required()) }}
              >
                {(field) => (
                  <input
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                  />
                )}
              </form.Field>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <form.Field
              name="email"
              validators={{
                onChange: composeValidators(required(), email()),
              }}
            >
              {(field) => (
                <input
                  type="email"
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              )}
            </form.Field>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Celular
            </label>
            <form.Field name="celular">
              {(field) => (
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              )}
            </form.Field>
          </div>

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Contrasena
              </label>
              <form.Field
                name="password"
                validators={{
                  onChange: composeValidators(required(), minLength(6)),
                }}
              >
                {(field) => (
                  <input
                    type="password"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                  />
                )}
              </form.Field>
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Confirmar contrasena
              </label>
              <form.Field
                name="confirmPassword"
                validators={{
                  onChange: composeValidators(required(), minLength(6)),
                }}
              >
                {(field) => (
                  <input
                    type="password"
                    value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                  />
                )}
              </form.Field>
            </div>
          </div>

          {/* Role selection with visual toggle pills */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Roles
            </label>
            <div className="flex flex-wrap gap-2">
              {todosRoles.map((rol) => (
                <button
                  key={rol.codigo}
                  type="button"
                  onClick={() => toggleRol(rol.codigo)}
                  className={`px-3 py-1 rounded text-sm border cursor-pointer transition-colors ${
                    rolesSel.includes(rol.codigo)
                      ? "bg-blue-600 text-white border-blue-600"
                      : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                  }`}
                >
                  {rol.nombre}
                </button>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-100 cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={guardando}
              className="px-4 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 cursor-pointer"
            >
              {guardando ? "Creando..." : "Crear usuario"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Pagina principal ── */

/**
 * AdminUsuariosPage — Main page component.
 *
 * Guard: redirects non-ADMIN users to /productos on mount.
 *
 * State:
 *   - usuarios: paginated user list from the backend.
 *   - rolFiltro: optional role filter sent to the API.
 *   - editando/creando: controls which modal is open (if any).
 *   - mensaje/error: feedback banners with 3-second auto-dismiss.
 *
 * The "Eliminar" button is hidden for ADMIN users (self-preservation).
 */
export default function AdminUsuariosPage() {
  const navigate = useNavigate();
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rolFiltro, setRolFiltro] = useState("");
  const [todosRoles, setTodosRoles] = useState<RolOption[]>([]);
  const [editando, setEditando] = useState<Usuario | null>(null);
  const [creando, setCreando] = useState(false);

  // Guard: only ADMIN can view this page
  const userRoles = getUserRoles();
  const esAdmin = userRoles.includes("ADMIN");
  useEffect(() => {
    if (!esAdmin) {
      navigate("/productos", { replace: true });
    }
  }, [esAdmin, navigate]);

  /** Shows a success banner that auto-clears after 3 seconds. */
  const mostrarMensaje = (msg: string) => {
    setMensaje(msg);
    setTimeout(() => setMensaje(null), 3000);
  };

  // Load all roles for filter dropdown and modal (only if admin)
  useEffect(() => {
    if (!esAdmin) return;
    apiFetch<RolOption[]>("/roles/")
      .then(setTodosRoles)
      .catch(() => {});
  }, [esAdmin]);

  /** Fetches the paginated user list, optionally filtered by a role code. */
  const loadUsuarios = useCallback(async () => {
    if (!esAdmin) return;
    setLoading(true);
    setError(null);
    try {
      const data = await usuariosApi.getAll(
        page * PAGE_SIZE,
        PAGE_SIZE,
        rolFiltro || undefined
      );
      setUsuarios(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, rolFiltro, esAdmin]);

  useEffect(() => {
    loadUsuarios();
  }, [loadUsuarios]);

  /** Persists user edits to the backend. */
  const handleSave = async (id: number, data: UsuarioUpdate) => {
    await usuariosApi.update(id, data);
    mostrarMensaje("Usuario actualizado");
    loadUsuarios();
  };

  /** Persists a new user to the backend. */
  const handleCreate = async (data: UsuarioCreate) => {
    await usuariosApi.create(data);
    mostrarMensaje("Usuario creado exitosamente");
    setCreando(false);
    loadUsuarios();
  };

  /** Deletes a user after confirmation. ADMIN users cannot be deleted. */
  const handleDelete = async (id: number) => {
    if (!confirm("Estas seguro de eliminar este usuario?")) return;
    try {
      await usuariosApi.delete(id);
      mostrarMensaje("Usuario eliminado");
      loadUsuarios();
    } catch (e) {
      setError((e as Error).message);
      setTimeout(() => setError(null), 3000);
    }
  };

  /** Color mapping for role badges. */
  const coloresRol: Record<string, string> = {
    ADMIN: "bg-red-100 text-red-800",
    STOCK: "bg-yellow-100 text-yellow-800",
    PEDIDOS: "bg-blue-100 text-blue-800",
    CLIENT: "bg-green-100 text-green-800",
  };

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Gestion de Usuarios</h1>
        <button
          onClick={() => setCreando(true)}
          className="bg-green-600 text-white px-4 py-2 rounded text-sm hover:bg-green-700 cursor-pointer"
        >
          + Crear Usuario
        </button>
      </div>

      {/* Feedback banners */}
      {mensaje && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-2 rounded mb-4">
          {mensaje}
        </div>
      )}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}

      {/* Role filter dropdown */}
      <div className="flex gap-2 mb-4 items-center">
        <label className="text-sm font-medium text-gray-700">Filtrar por rol:</label>
        <select
          value={rolFiltro}
          onChange={(e) => {
            setRolFiltro(e.target.value);
            setPage(0);
          }}
          className="border border-gray-300 rounded px-3 py-1.5 text-sm"
        >
          <option value="">Todos los roles</option>
          {todosRoles.map((rol) => (
            <option key={rol.codigo} value={rol.codigo}>
              {rol.nombre}
            </option>
          ))}
        </select>
      </div>

      {/* Loading / empty / table */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Cargando usuarios...</span>
          </div>
      ) : usuarios.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p className="text-lg">No se encontraron usuarios</p>
        </div>
      ) : (
        <table className="w-full border-collapse border">
          <thead>
            <tr className="bg-gray-200">
              <th className="border p-2 text-left">Legajo</th>
              <th className="border p-2 text-left">Nombre</th>
              <th className="border p-2 text-left">Email</th>
              <th className="border p-2 text-left">Roles</th>
              <th className="border p-2 text-left">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {usuarios.map((u) => (
              <tr key={u.id} className="hover:bg-gray-100 border-b">
                <td className="border p-2 font-mono">{u.id}</td>
                <td className="border p-2">
                  {u.nombre} {u.apellido}
                </td>
                <td className="border p-2 text-sm text-gray-600">
                  {u.email}
                </td>
                {/* Role badges with role-specific colors */}
                <td className="border p-2">
                  <div className="flex gap-1 flex-wrap">
                    {u.roles.map((rol) => (
                      <span
                        key={rol.codigo}
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                          coloresRol[rol.codigo] || "bg-gray-100 text-gray-800"
                        }`}
                      >
                        {rol.nombre}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="border p-2">
                  <div className="flex gap-1">
                    <button
                      onClick={() => setEditando(u)}
                      className="bg-yellow-500 text-white px-3 py-1 rounded text-xs hover:bg-yellow-600 cursor-pointer"
                    >
                      Editar
                    </button>
                    {/* Prevent deletion of ADMIN users (self-preservation) */}
                    {u.roles.every((r) => r.codigo !== "ADMIN") && (
                      <button
                        onClick={() => handleDelete(u.id)}
                        className="bg-red-600 text-white px-3 py-1 rounded text-xs hover:bg-red-700 cursor-pointer"
                      >
                        Eliminar
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Pagination */}
      <div className="flex gap-2 mt-4 items-center">
        <button
          disabled={page === 0}
          onClick={() => setPage((p) => p - 1)}
          className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer"
        >
          Anterior
        </button>
        <span>Pagina {page + 1}</span>
        <button
          disabled={usuarios.length < PAGE_SIZE}
          onClick={() => setPage((p) => p + 1)}
          className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer"
        >
          Siguiente
        </button>
      </div>

      {/* Create modal */}
      {creando && (
        <CrearUsuarioModal
          todosRoles={todosRoles}
          onClose={() => setCreando(false)}
          onSave={handleCreate}
        />
      )}

      {/* Edit modal */}
      {editando && (
        <EditarUsuarioModal
          usuario={editando}
          todosRoles={todosRoles}
          onClose={() => setEditando(null)}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
