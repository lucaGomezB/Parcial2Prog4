import { useEffect, useState, useCallback } from "react";
import { useAppForm, required } from "../hooks/useAppForm";
import {
  direccionesApi,
  formatDireccion,
  type DireccionEntrega,
  type DireccionEntregaInput,
  type DireccionEntregaUpdate,
} from "../api/direcciones";

/* ── Modal compartido para crear/editar ── */

interface DireccionFormFields {
  alias: string;
  linea1: string;
  linea2: string;
  ciudad: string;
  provincia: string;
  codigo_postal: string;
  es_principal: boolean;
}

function DireccionModal({
  direccion,
  onClose,
  onSave,
}: {
  direccion?: DireccionEntrega;       // undefined → crear, defined → editar
  onClose: () => void;
  onSave: (data: DireccionEntregaInput | DireccionEntregaUpdate) => Promise<void>;
}) {
  const esEditar = !!direccion;

  const form = useAppForm<DireccionFormFields>({
    defaultValues: {
      alias: direccion?.alias ?? "",
      linea1: direccion?.linea1 ?? "",
      linea2: direccion?.linea2 ?? "",
      ciudad: direccion?.ciudad ?? "",
      provincia: direccion?.provincia ?? "",
      codigo_postal: direccion?.codigo_postal ?? "",
      es_principal: direccion?.es_principal ?? false,
    },
    onSubmit: async ({ value }) => {
      const base = {
        alias: value.alias.trim() || null,
        linea1: value.linea1.trim(),
        linea2: value.linea2.trim() || null,
        ciudad: value.ciudad.trim(),
        provincia: value.provincia.trim() || null,
        codigo_postal: value.codigo_postal.trim() || null,
      };
      if (esEditar) {
        await onSave({ ...base, es_principal: value.es_principal } satisfies DireccionEntregaUpdate & { es_principal: boolean });
      } else {
        await onSave({ ...base, es_principal: value.es_principal } satisfies DireccionEntregaInput);
      }
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-4">
          {esEditar ? "Editar Dirección" : "Nueva Dirección"}
        </h2>
        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="space-y-3">
          <form.Field name="alias">
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Alias</label>
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Ej: Casa, Trabajo..."
                  maxLength={50}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              </div>
            )}
          </form.Field>
          <form.Field
            name="linea1"
            validators={{ onChange: required() }}
          >
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Calle y Número <span className="text-red-500">*</span>
                </label>
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Av. Siempre Viva 123"
                  required
                  maxLength={100}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              </div>
            )}
          </form.Field>
          <form.Field name="linea2">
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Piso / Dpto</label>
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Piso 3, Dpto B"
                  maxLength={100}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              </div>
            )}
          </form.Field>
          <div className="flex gap-3">
            <div className="flex-1">
              <form.Field
                name="ciudad"
                validators={{ onChange: required() }}
              >
                {(field) => (
                  <>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Ciudad <span className="text-red-500">*</span>
                    </label>
                    <input
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      placeholder="Ciudad"
                      required
                      maxLength={100}
                      className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                    />
                  </>
                )}
              </form.Field>
            </div>
            <div className="flex-1">
              <form.Field name="provincia">
                {(field) => (
                  <>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Provincia</label>
                    <input
                      value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      placeholder="Provincia"
                      maxLength={100}
                      className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                    />
                  </>
                )}
              </form.Field>
            </div>
          </div>
          <form.Field name="codigo_postal">
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Código Postal</label>
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="5000"
                  maxLength={10}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              </div>
            )}
          </form.Field>

          <form.Field name="es_principal">
            {(field) => (
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={field.state.value}
                  onChange={(e) => field.handleChange(e.target.checked)}
                  onBlur={field.handleBlur}
                  className="cursor-pointer"
                />
                <span className="font-medium text-gray-700">Marcar como dirección principal</span>
              </label>
            )}
          </form.Field>

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
              disabled={form.state.isSubmitting || !form.state.values.linea1.trim() || !form.state.values.ciudad.trim()}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
            >
              {form.state.isSubmitting ? "Guardando..." : esEditar ? "Actualizar" : "Crear"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
/* ── Página principal ── */
export default function DireccionesPage() {
  const [direcciones, setDirecciones] = useState<DireccionEntrega[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState<DireccionEntrega | undefined>(undefined);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await direccionesApi.getAll();
      // Ordenar: principal primero, luego por created_at DESC
      data.sort((a, b) => {
        if (a.es_principal !== b.es_principal) return a.es_principal ? -1 : 1;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
      setDirecciones(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const mostrarMensaje = (msg: string) => {
    setMensaje(msg);
    setTimeout(() => setMensaje(null), 3000);
  };

  const handleCreate = async (data: DireccionEntregaInput) => {
    await direccionesApi.create(data);
    mostrarMensaje("Dirección creada");
    load();
  };

  const handleUpdate = async (id: number, data: DireccionEntregaUpdate & { es_principal?: boolean }) => {
    const { es_principal, ...updateData } = data;
    await direccionesApi.update(id, updateData);
    if (es_principal) {
      await direccionesApi.setPrincipal(id);
    }
    mostrarMensaje("Dirección actualizada");
    load();
  };

  const handleSetPrincipal = async (id: number) => {
    try {
      await direccionesApi.setPrincipal(id);
      mostrarMensaje("Dirección marcada como principal");
      load();
    } catch (e) {
      setError((e as Error).message);
      setTimeout(() => setError(null), 3000);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("¿Estás seguro de eliminar esta dirección?")) return;
    try {
      await direccionesApi.delete(id);
      mostrarMensaje("Dirección eliminada");
      load();
    } catch (e) {
      setError((e as Error).message);
      setTimeout(() => setError(null), 3000);
    }
  };

  const abrirEditar = (d: DireccionEntrega) => {
    setEditando(d);
    setShowModal(true);
  };

  const cerrarModal = () => {
    setShowModal(false);
    setEditando(undefined);
  };

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Mis Direcciones</h1>
        <button
          onClick={() => { setEditando(undefined); setShowModal(true); }}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 cursor-pointer"
        >
          + Nueva Dirección
        </button>
      </div>

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

      {loading ? (
        <p className="text-gray-500">Cargando direcciones...</p>
      ) : direcciones.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p className="text-lg mb-2">No tenés direcciones de entrega</p>
          <p className="text-sm">Agregá una dirección para recibir pedidos.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {direcciones.map((d) => (
            <div
              key={d.id}
              className="border border-gray-200 rounded p-4 flex justify-between items-start hover:bg-gray-50"
            >
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold">
                    {formatDireccion(d)}
                  </span>
                  {d.es_principal && (
                    <span className="inline-block bg-green-100 text-green-800 text-xs font-medium px-2 py-0.5 rounded">
                      Principal
                    </span>
                  )}
                </div>
                {d.linea2 && (
                  <p className="text-sm text-gray-500">{d.linea2}</p>
                )}
                <div className="text-xs text-gray-400 mt-1">
                  {[d.provincia, d.codigo_postal].filter(Boolean).join(" — ")}
                </div>
              </div>

              <div className="flex gap-1 ml-4">
                <button
                  onClick={() => abrirEditar(d)}
                  className="bg-gray-600 text-white px-3 py-1 rounded text-xs hover:bg-gray-700 cursor-pointer"
                >
                  Editar
                </button>
                {!d.es_principal && (
                  <button
                    onClick={() => handleSetPrincipal(d.id)}
                    className="bg-green-600 text-white px-3 py-1 rounded text-xs hover:bg-green-700 cursor-pointer"
                  >
                    Principal
                  </button>
                )}
                <button
                  onClick={() => handleDelete(d.id)}
                  className="bg-red-600 text-white px-3 py-1 rounded text-xs hover:bg-red-700 cursor-pointer"
                >
                  Eliminar
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal crear/editar */}
      {showModal && (
        <DireccionModal
          direccion={editando}
          onClose={cerrarModal}
          onSave={async (data) => {
            if (editando) {
              await handleUpdate(editando.id, data as DireccionEntregaUpdate);
            } else {
              await handleCreate(data as DireccionEntregaInput);
            }
          }}
        />
      )}
    </div>
  );
}
