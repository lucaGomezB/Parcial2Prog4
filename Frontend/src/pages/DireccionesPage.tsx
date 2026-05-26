import { useEffect, useState, useCallback } from "react";
import {
  direccionesApi,
  formatDireccion,
  type DireccionEntrega,
  type DireccionEntregaInput,
  type DireccionEntregaUpdate,
} from "../api/direcciones";

/* ── Modal compartido para crear/editar ── */
function DireccionModal({
  direccion,
  onClose,
  onSave,
}: {
  direccion?: DireccionEntrega;       // undefined → crear, defined → editar
  onClose: () => void;
  onSave: (data: DireccionEntregaInput | DireccionEntregaUpdate) => Promise<void>;
}) {
  const [alias, setAlias] = useState(direccion?.alias ?? "");
  const [linea1, setLinea1] = useState(direccion?.linea1 ?? "");
  const [linea2, setLinea2] = useState(direccion?.linea2 ?? "");
  const [ciudad, setCiudad] = useState(direccion?.ciudad ?? "");
  const [provincia, setProvincia] = useState(direccion?.provincia ?? "");
  const [codigoPostal, setCodigoPostal] = useState(direccion?.codigo_postal ?? "");
  const [esPrincipal, setEsPrincipal] = useState(direccion?.es_principal ?? false);
  const [guardando, setGuardando] = useState(false);

  const esEditar = !!direccion;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!linea1.trim() || !ciudad.trim()) return;
    setGuardando(true);
    try {
      const base = {
        alias: alias.trim() || null,
        linea1: linea1.trim(),
        linea2: linea2.trim() || null,
        ciudad: ciudad.trim(),
        provincia: provincia.trim() || null,
        codigo_postal: codigoPostal.trim() || null,
      };
      if (esEditar) {
        await onSave({ ...base, es_principal: esPrincipal } satisfies DireccionEntregaUpdate & { es_principal: boolean });
      } else {
        await onSave({ ...base, es_principal: esPrincipal } satisfies DireccionEntregaInput);
      }
      onClose();
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-4">
          {esEditar ? "Editar Dirección" : "Nueva Dirección"}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Alias</label>
            <input
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="Ej: Casa, Trabajo..."
              maxLength={50}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Calle y Número <span className="text-red-500">*</span>
            </label>
            <input
              value={linea1}
              onChange={(e) => setLinea1(e.target.value)}
              placeholder="Av. Siempre Viva 123"
              required
              maxLength={100}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Piso / Dpto</label>
            <input
              value={linea2}
              onChange={(e) => setLinea2(e.target.value)}
              placeholder="Piso 3, Dpto B"
              maxLength={100}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Ciudad <span className="text-red-500">*</span>
              </label>
              <input
                value={ciudad}
                onChange={(e) => setCiudad(e.target.value)}
                placeholder="Ciudad"
                required
                maxLength={100}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Provincia</label>
              <input
                value={provincia}
                onChange={(e) => setProvincia(e.target.value)}
                placeholder="Provincia"
                maxLength={100}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Código Postal</label>
            <input
              value={codigoPostal}
              onChange={(e) => setCodigoPostal(e.target.value)}
              placeholder="5000"
              maxLength={10}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>

          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={esPrincipal}
              onChange={(e) => setEsPrincipal(e.target.checked)}
              className="cursor-pointer"
            />
            <span className="font-medium text-gray-700">Marcar como dirección principal</span>
          </label>

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
              disabled={guardando || !linea1.trim() || !ciudad.trim()}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
            >
              {guardando ? "Guardando..." : esEditar ? "Actualizar" : "Crear"}
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
