/**
 * DireccionesPage — Delivery addresses management page for authenticated users.
 * Uses TanStack Query for data fetching and mutations.
 * Uses DataTable with client-side pagination.
 * Role-adaptive: ADMIN sees "Administracion de sucursales", CLIENT sees "Mis Direcciones".
 */
import { useState, useMemo } from "react";
import { AxiosError } from "axios";
import { useAppForm, required } from "@/shared/hooks/useAppForm";
import { addToast } from "@/shared/components/Toast";
import { formatValidationErrors } from "@/shared/utils/fieldLabels";
import DataTable, { type DataTableColumn } from "@/shared/components/DataTable";
import {
  type DireccionEntrega,
  type DireccionEntregaInput,
  type DireccionEntregaUpdate,
} from "@/features/pedidos/api/direcciones";
import {
  useDirecciones,
  useCreateDireccion,
  useUpdateDireccion,
  useDeleteDireccion,
  useSetPrincipalDireccion,
} from "@/features/pedidos/hooks/useDirecciones";
import ErrorBanner from "@/shared/components/ErrorBanner";
import { EditButton, DeleteButton } from "@/shared/components/ActionButton";
import FormFooter from "@/shared/components/FormFooter";
import SearchFilter from "@/shared/components/SearchFilter";
import { getUserRoles } from "@/shared/api/client";

const DEFAULT_LIMIT = 10;

/* ── Modal compartido para crear/editar ── */

interface DireccionFormFields {
  alias: string;
  linea1: string;
  linea2: string;
  ciudad: string;
  provincia: string;
  codigo_postal: string;
  es_principal: boolean;
  es_local: boolean;
}

function DireccionModal({
  direccion,
  onClose,
  onSave,
}: {
  direccion?: DireccionEntrega;
  onClose: () => void;
  onSave: (data: DireccionEntregaInput | DireccionEntregaUpdate) => Promise<void>;
}) {
  const esEditar = !!direccion;
  const [modalError, setModalError] = useState<string | null>(null);
  const isAdmin = getUserRoles().includes("ADMIN");

  const form = useAppForm<DireccionFormFields>({
    defaultValues: {
      alias: direccion?.alias ?? "",
      linea1: direccion?.linea1 ?? "",
      linea2: direccion?.linea2 ?? "",
      ciudad: direccion?.ciudad ?? "",
      provincia: direccion?.provincia ?? "",
      codigo_postal: direccion?.codigo_postal ?? "",
      es_principal: direccion?.es_principal ?? false,
      es_local: direccion?.es_local ?? isAdmin,
    },
    onSubmit: async ({ value }: { value: DireccionFormFields }) => {
      const base = {
        alias: value.alias.trim() || null,
        linea1: value.linea1.trim(),
        linea2: value.linea2.trim() || null,
        ciudad: value.ciudad.trim(),
        provincia: value.provincia.trim() || null,
        codigo_postal: value.codigo_postal.trim() || null,
      };
      try {
        if (esEditar) {
          await onSave({ ...base, es_principal: value.es_principal, es_local: isAdmin ? true : value.es_local } satisfies DireccionEntregaUpdate & { es_principal: boolean; es_local: boolean });
        } else {
          await onSave({ ...base, es_principal: value.es_principal, es_local: isAdmin ? true : value.es_local } satisfies DireccionEntregaInput);
        }
        onClose();
      } catch (err) {
        if (err instanceof AxiosError && err.response?.data) {
          const body = err.response.data as Record<string, unknown>;
          if (body.errors && Array.isArray(body.errors)) {
            const messages = formatValidationErrors(body.errors as Array<{ loc: string[]; msg: string; type: string }>);
            setModalError(messages.join('\n'));
          } else {
            setModalError("Error al guardar la direccion. Intente nuevamente.");
          }
        } else {
          setModalError("Error al guardar la direccion. Intente nuevamente.");
        }
        setTimeout(() => setModalError(null), 4000);
      }
    },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-4">{esEditar ? "Editar Direccion" : "Nueva Direccion"}</h2>
        {modalError && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4 text-sm">{modalError}</div>}
        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="space-y-3">
          <form.Field name="alias">
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Alias</label>
                <input value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} placeholder="Ej: Casa, Trabajo..." maxLength={50} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
              </div>
            )}
          </form.Field>
          <form.Field name="linea1" validators={{ onChange: required() }}>
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Calle y Numero <span className="text-red-500">*</span></label>
                <input value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} placeholder="Av. Siempre Viva 123" required maxLength={100} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
              </div>
            )}
          </form.Field>
          <form.Field name="linea2">
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Piso / Dpto</label>
                <input value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} placeholder="Piso 3, Dpto B" maxLength={100} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
              </div>
            )}
          </form.Field>
          <div className="flex gap-3">
            <div className="flex-1">
              <form.Field name="ciudad" validators={{ onChange: required() }}>
                {(field) => (
                  <>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Ciudad <span className="text-red-500">*</span></label>
                    <input value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} placeholder="Ciudad" required maxLength={100} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
                  </>
                )}
              </form.Field>
            </div>
            <div className="flex-1">
              <form.Field name="provincia">
                {(field) => (
                  <>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Provincia</label>
                    <input value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} placeholder="Provincia" maxLength={100} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
                  </>
                )}
              </form.Field>
            </div>
          </div>
          <form.Field name="codigo_postal">
            {(field) => (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Codigo Postal</label>
                <input value={field.state.value} onChange={(e) => field.handleChange(e.target.value)} onBlur={field.handleBlur} placeholder="5000" maxLength={10} className="w-full border border-gray-300 rounded px-3 py-2 text-sm" />
              </div>
            )}
          </form.Field>
          {/* Solo CLIENT puede marcar una direccion como principal. ADMIN gestiona locales, no tiene direccion principal. */}
          {!isAdmin && (
            <form.Field name="es_principal">
              {(field) => (
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input type="checkbox" checked={field.state.value} onChange={(e) => field.handleChange(e.target.checked)} onBlur={field.handleBlur} className="cursor-pointer" />
                  <span className="font-medium text-gray-700">Marcar como direccion principal</span>
                </label>
              )}
            </form.Field>
          )}
          <div className="flex justify-end pt-2">
            <FormFooter
              isSubmitting={form.state.isSubmitting}
              isEditing={esEditar}
              onCancel={onClose}
            />
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Pagina principal ── */

export default function DireccionesPage() {
  const [showModal, setShowModal] = useState(false);
  const [editando, setEditando] = useState<DireccionEntrega | undefined>(undefined);
  const [skip, setSkip] = useState(0);
  const [limit, setLimit] = useState(DEFAULT_LIMIT);
  const [search, setSearch] = useState("");

  const esAdmin = getUserRoles().includes("ADMIN");

  // ── TanStack Query ──
  const { data: direccionesRaw = [], isLoading, isError, error } = useDirecciones();
  const createMutation = useCreateDireccion();
  const updateMutation = useUpdateDireccion();
  const deleteMutation = useDeleteDireccion();
  const setPrincipalMutation = useSetPrincipalDireccion();

  // Sort: principal first, then by created_at DESC
  const direcciones = useMemo(() => {
    const sorted = [...direccionesRaw];
    sorted.sort((a, b) => {
      if (a.es_principal !== b.es_principal) return a.es_principal ? -1 : 1;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    return sorted;
  }, [direccionesRaw]);

  // Client-side search filter on alias, linea1, ciudad
  const filteredDirecciones = useMemo(() => {
    if (!search.trim()) return direcciones;
    const s = search.toLowerCase();
    return direcciones.filter(
      (d) =>
        (d.alias ?? "").toLowerCase().includes(s) ||
        d.linea1.toLowerCase().includes(s) ||
        d.ciudad.toLowerCase().includes(s)
    );
  }, [direcciones, search]);

  // Client-side pagination
  const total = filteredDirecciones.length;
  const pagedDirecciones = filteredDirecciones.slice(skip, skip + limit);

  const handleCreate = async (data: DireccionEntregaInput) => {
    await createMutation.mutateAsync(data);
    addToast('exito', "Direccion creada");
  };

  const handleUpdate = async (id: number, data: DireccionEntregaUpdate & { es_principal?: boolean }) => {
    await updateMutation.mutateAsync({ id, data });
    addToast('exito', "Direccion actualizada");
  };

  const handleSetPrincipal = async (id: number) => {
    try {
      await setPrincipalMutation.mutateAsync(id);
      addToast('exito', "Direccion marcada como principal");
    } catch (e) {
      if (e instanceof AxiosError && e.response?.data) {
        const body = e.response.data as Record<string, unknown>;
        if (body.errors && Array.isArray(body.errors)) {
          const messages = formatValidationErrors(body.errors as Array<{ loc: string[]; msg: string; type: string }>);
          messages.forEach((m) => addToast('error', m));
        } else {
          addToast('error', (e as Error).message);
        }
      } else {
        addToast('error', (e as Error).message);
      }
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Estas seguro de eliminar esta direccion?")) return;
    try {
      await deleteMutation.mutateAsync(id);
      addToast('exito', "Direccion eliminada");
    } catch (e) {
      if (e instanceof AxiosError && e.response?.data) {
        const body = e.response.data as Record<string, unknown>;
        if (body.errors && Array.isArray(body.errors)) {
          const messages = formatValidationErrors(body.errors as Array<{ loc: string[]; msg: string; type: string }>);
          messages.forEach((m) => addToast('error', m));
        } else {
          addToast('error', (e as Error).message);
        }
      } else {
        addToast('error', (e as Error).message);
      }
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

  const handlePageChange = (newSkip: number) => setSkip(newSkip);
  const handleLimitChange = (newLimit: number) => { setLimit(newLimit); setSkip(0); };

  const columns: DataTableColumn<DireccionEntrega>[] = [
    {
      key: "alias",
      label: "Alias",
      render: (d) => (
        <div className="flex items-center gap-2">
          <span className="font-semibold">{d.alias || "—"}</span>
          {d.es_principal && (
            <span className="inline-block bg-green-100 text-green-800 text-xs font-medium px-2 py-0.5 rounded">
              Principal
            </span>
          )}
        </div>
      ),
    },
    {
      key: "direccion",
      label: "Direccion",
      render: (d) => (
        <div>
          <span className="text-sm">{d.linea1}, {d.ciudad}</span>
          {d.linea2 && <p className="text-xs text-gray-500">{d.linea2}</p>}
          <div className="text-xs text-gray-400">
            {[d.provincia, d.codigo_postal].filter(Boolean).join(" - ")}
          </div>
        </div>
      ),
    },
    {
      key: "ciudad",
      label: "Ciudad",
      hideOnMobile: true,
      render: (d) => <span className="text-sm text-gray-600">{d.ciudad}</span>,
    },
    ...(esAdmin ? [{
      key: "es_local" as const,
      label: "Tipo",
      render: (d: DireccionEntrega) => (
        d.es_local ? (
          <span className="inline-block bg-green-100 text-green-800 text-xs font-medium px-2 py-0.5 rounded">Local</span>
        ) : (
          <span className="inline-block bg-gray-100 text-gray-600 text-xs font-medium px-2 py-0.5 rounded">Personal</span>
        )
      ),
    }] : []),
    {
      key: "acciones",
      label: "Acciones",
      render: (d) => (
        <div className="flex gap-1">
          <EditButton onClick={() => abrirEditar(d)} />
          {/* Solo CLIENT puede marcar principal. ADMIN gestiona locales, no direcciones personales. */}
          {!esAdmin && !d.es_principal && (
            <button onClick={() => handleSetPrincipal(d.id)} className="bg-green-600 text-white px-3 py-1 rounded text-xs hover:bg-green-700 cursor-pointer">Principal</button>
          )}
          <DeleteButton onClick={() => handleDelete(d.id)} />
        </div>
      ),
    },
  ];

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h1 className="text-2xl font-bold">
            {esAdmin ? "Administracion de sucursales Food Store" : "Mis direcciones de Entrega"}
          </h1>
          {esAdmin && (
            <p className="text-sm text-gray-500 mt-1">
              Los locales creados aqui estaran disponibles como puntos de retiro para todos los clientes.
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <SearchFilter
            onSearch={(v) => { setSearch(v); setSkip(0); }}
            placeholder="Buscar direccion..."
          />
          <button onClick={() => { setEditando(undefined); setShowModal(true); }} className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 cursor-pointer">{esAdmin ? "+ Nuevo Local" : "+ Nueva Direccion"}</button>
        </div>
      </div>
      <ErrorBanner isError={isError} error={error} message="Error al cargar" />
      <DataTable
        columns={columns}
        data={pagedDirecciones}
        total={total}
        skip={skip}
        limit={limit}
        onPageChange={handlePageChange}
        onLimitChange={handleLimitChange}
        isLoading={isLoading}
        emptyMessage="No tenes direcciones de entrega. Agrega una direccion para recibir pedidos."
      />
      {showModal && (
        <DireccionModal direccion={editando} onClose={cerrarModal} onSave={async (data) => {
          if (editando) { await handleUpdate(editando.id, data as DireccionEntregaUpdate); } else { await handleCreate(data as DireccionEntregaInput); }
        }} />
      )}
    </div>
  );
}
