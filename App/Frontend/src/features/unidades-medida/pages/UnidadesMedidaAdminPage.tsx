/**
 * UnidadesMedidaAdminPage — Admin CRUD page for measurement units.
 *
 * Features:
 *   - Data table with columns: Nombre, Simbolo, Tipo, Acciones
 *   - Filter tabs/dropdown by tipo (todos, masa, volumen, unidad, area)
 *   - Inline create/edit form via UnidadMedidaForm
 *   - Delete with confirmation dialog; FK-protected (catches 400 errors)
 *   - Client-side pagination via DataTable
 *   - Gated to ADMIN role via router
 */
import { useState, useEffect, useCallback, useMemo } from "react";
import { AxiosError } from "axios";
import type { UnidadMedida, UnidadMedidaCreate } from "@/features/unidades-medida/types";
import { unidadesMedidaApi } from "@/features/unidades-medida/api/unidadesMedidaApi";
import UnidadMedidaForm from "@/features/unidades-medida/components/UnidadMedidaForm";
import { addToast } from "@/shared/components/Toast";
import { formatValidationErrors } from "@/shared/utils/fieldLabels";
import ErrorBanner from "@/shared/components/ErrorBanner";
import DataTable, { type DataTableColumn } from "@/shared/components/DataTable";
import { usePagination } from "@/shared/hooks/usePagination";
import { EditButton, DeleteButton } from "@/shared/components/ActionButton";
import SearchFilter from "@/shared/components/SearchFilter";

const DEFAULT_LIMIT = 10;

const TIPO_FILTERS = [
  { value: "", label: "Todos" },
  { value: "masa", label: "Masa" },
  { value: "volumen", label: "Volumen" },
  { value: "unidad", label: "Unidad" },
  { value: "area", label: "Area" },
];

export default function UnidadesMedidaAdminPage() {
  const [units, setUnits] = useState<UnidadMedida[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [tipoFilter, setTipoFilter] = useState("");
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editValues, setEditValues] = useState<UnidadMedidaCreate | undefined>();
  const [submitting, setSubmitting] = useState(false);

  const { skip, limit, handlePageChange, handleLimitChange } = usePagination(DEFAULT_LIMIT);

  const fetchUnits = useCallback(async () => {
    setLoading(true);
    try {
      const data = await unidadesMedidaApi.getAll(tipoFilter || undefined);
      setUnits(data);
      setError(null);
    } catch {
      setError("Error al cargar unidades de medida");
      addToast("error", "Error al cargar unidades de medida");
    } finally {
      setLoading(false);
    }
  }, [tipoFilter]);

  useEffect(() => {
    void fetchUnits();
  }, [fetchUnits]);

  const handleCreate = () => {
    setEditingId(null);
    setEditValues(undefined);
    setShowForm(true);
  };

  const handleEdit = (unit: UnidadMedida) => {
    setEditingId(unit.id);
    setEditValues({ nombre: unit.nombre, simbolo: unit.simbolo, tipo: unit.tipo, factor_conversion: unit.factor_conversion });
    setShowForm(true);
  };

  const handleFormSubmit = async (data: UnidadMedidaCreate) => {
    setSubmitting(true);
    try {
      if (editingId) {
        await unidadesMedidaApi.update(editingId, {
          nombre: data.nombre,
          simbolo: data.simbolo,
          tipo: data.tipo,
          factor_conversion: data.factor_conversion,
        });
        addToast("exito", "Unidad de medida actualizada correctamente");
      } else {
        await unidadesMedidaApi.create(data);
        addToast("exito", "Unidad de medida creada correctamente");
      }
      setShowForm(false);
      setEditingId(null);
      void fetchUnits();
    } catch (err) {
      if (err instanceof AxiosError && err.response?.data) {
        const body = err.response.data as Record<string, unknown>;
        if (body.errors && Array.isArray(body.errors)) {
          const messages = formatValidationErrors(body.errors as Array<{ loc: string[]; msg: string; type: string }>);
          messages.forEach((m) => addToast("error", m));
        } else {
          addToast("error", (err as Error)?.message || "Error al guardar");
        }
      } else {
        addToast("error", (err as Error)?.message || "Error al guardar");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (unit: UnidadMedida) => {
    if (!confirm(`Eliminar la unidad "${unit.nombre}"?`)) return;
    try {
      await unidadesMedidaApi.remove(unit.id);
      addToast("exito", "Unidad de medida eliminada correctamente");
      void fetchUnits();
    } catch (err) {
      const msg = (err as Error)?.message || "";
      if (msg.toLowerCase().includes("uso") || msg.toLowerCase().includes("referencia")) {
        addToast("error", `No se puede eliminar: la unidad "${unit.nombre}" esta en uso`);
      } else {
        addToast("error", "Error al eliminar la unidad de medida");
      }
    }
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
  };

  // Client-side search filter + pagination
  const filteredUnits = useMemo(() => {
    if (!search.trim()) return units;
    const s = search.toLowerCase();
    return units.filter(
      (u) => u.nombre.toLowerCase().includes(s) || u.simbolo.toLowerCase().includes(s)
    );
  }, [units, search]);

  const total = filteredUnits.length;
  const pagedUnits = filteredUnits.slice(skip, skip + limit);

  const columns: DataTableColumn<UnidadMedida>[] = [
    {
      key: "nombre",
      label: "Nombre",
      render: (u) => <span className="font-semibold text-gray-900">{u.nombre}</span>,
    },
    {
      key: "simbolo",
      label: "Simbolo",
      render: (u) => <span className="text-sm text-gray-600">{u.simbolo}</span>,
    },
    {
      key: "tipo",
      label: "Tipo",
      render: (u) => <span className="text-sm text-gray-600 capitalize">{u.tipo}</span>,
    },
    {
      key: "acciones",
      label: "Acciones",
      render: (unit) => (
        <div className="flex gap-1">
          <EditButton onClick={() => handleEdit(unit)} />
          <DeleteButton onClick={() => handleDelete(unit)} />
        </div>
      ),
    },
  ];

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Unidades de Medida</h1>

      {error && <ErrorBanner isError={!!error} message={error} />}

      {/* Search filter */}
      <div className="mb-4">
        <SearchFilter
          onSearch={(v) => { setSearch(v); handlePageChange(0); }}
          placeholder="Filtrar por nombre o simbolo..."
        />
      </div>

      {/* Filter tabs + Create button */}
      <div className="flex gap-2 mb-4 flex-wrap items-center">
        {TIPO_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => { setTipoFilter(f.value); handlePageChange(0); }}
            className={`px-3 py-1 rounded text-sm cursor-pointer border ${
              tipoFilter === f.value
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
            }`}
          >
            {f.label}
          </button>
        ))}
        <span className="flex-1" />
        <button
          onClick={handleCreate}
          className="bg-green-600 text-white px-4 py-1.5 rounded cursor-pointer hover:bg-green-700"
        >
          + Nueva
        </button>
      </div>

      {/* Create/Edit form */}
      {showForm && (
        <UnidadMedidaForm
          editingId={editingId}
          initialValues={editValues}
          onSubmit={handleFormSubmit}
          onCancel={handleCancel}
          submitting={submitting}
        />
      )}

      {/* Data table with client-side pagination */}
      <DataTable
        columns={columns}
        data={pagedUnits}
        total={total}
        skip={skip}
        limit={limit}
        onPageChange={handlePageChange}
        onLimitChange={handleLimitChange}
        isLoading={loading}
      />
    </div>
  );
}
