/**
 * IngredientesCRUD — Ingredients (insumos) management admin page.
 * Uses TanStack Query for data fetching and mutations.
 * Uses DataTable with server-side pagination.
 */
import { useState, useEffect, useMemo, useRef, useLayoutEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { Ingrediente, IngredienteCreate, AfectadoProducto } from "@/features/productos/api/ingredientes";
import { ingredientesApi } from "@/features/productos/api/ingredientes";
import { useIngredientes, useCreateIngrediente, useUpdateIngrediente, useDeleteIngrediente } from "@/features/productos/hooks/useIngredientes";
import { queryKeys } from "@/shared/api/queryKeys";
import { exportToExcel } from "@/shared/utils/exportExcel";
import { parseApiError } from "@/shared/utils/apiErrors";
import { useAppForm } from "@/shared/hooks/useAppForm";
import { useStore } from "@tanstack/react-form";
import { addToast } from "@/shared/components/Toast";
import DataTable, { type DataTableColumn } from "@/shared/components/DataTable";
import type { UnidadMedida } from "@/features/unidades-medida/api/unidadesMedidaApi";
import { unidadesMedidaApi } from "@/features/unidades-medida/api/unidadesMedidaApi";
import type { UnidadMedidaTipo } from "@/features/unidades-medida/types";
import CrudToolbar from "@/shared/components/CrudToolbar";
import ConfirmDialog from "@/shared/components/ConfirmDialog";
import { useCrudTable } from "@/shared/hooks/useCrudTable";
import { useDebounce } from "@/shared/hooks/useDebounce";
import { getUserRoles } from "@/shared/api/client";
import ErrorBanner from "@/shared/components/ErrorBanner";
import StockHistorialTab from "@/features/productos/components/StockHistorialTab";
import { EditButton, DeleteButton } from "@/shared/components/ActionButton";
import FormFooter from "@/shared/components/FormFooter";
import DecimalInput from "@/shared/components/DecimalInput";
import { formatCurrency } from "@/shared/utils/formatCurrency";

const DEFAULT_LIMIT = 10;

export default function IngredientesCRUD() {
  const crud = useCrudTable({ defaultLimit: DEFAULT_LIMIT, defaultSortBy: 'id', defaultSortOrder: 'desc' });
  const { search, setSearch, sortBy, sortOrder, skip, limit, handlePageChange, handleLimitChange } = crud;
  const debouncedSearch = useDebounce(search, 500);

  const handleSort = (newSortBy: string, newSortOrder: "asc" | "desc") => {
    crud.handleSort(newSortBy, newSortOrder);
  };

  const userRoles = getUserRoles();
  const esAdmin = userRoles.includes("ADMIN");
  const esStock = userRoles.includes("STOCK");
  const showId = esAdmin || esStock;

  const [editingId, setEditingId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [unidades, setUnidades] = useState<UnidadMedida[]>([]);
  const [unidadTipoFilter, setUnidadTipoFilter] = useState<UnidadMedidaTipo | null>(null);
  const prevUnidadMedidaIdRef = useRef<number | null>(null);

  // ── Open edit form from query param (e.g. /ingredientes?edit=5) ──
  const [searchParams] = useSearchParams();
  const queryEditId = useMemo(() => {
    const editParam = searchParams.get("edit");
    if (editParam) {
      const id = Number(editParam);
      if (!isNaN(id) && id > 0) return id;
    }
    return null;
  }, [searchParams]);
  const queryEditTriggered = useRef(false);

  // ── Affected products: show which products depend on a selected ingredient ──
  const [selectedIngId, setSelectedIngId] = useState<number | null>(null);

  const {
    data: afectadosData,
  } = useQuery<AfectadoProducto[]>({
    queryKey: queryKeys.ingredientes.productosAfectados(selectedIngId ?? 0),
    queryFn: () => ingredientesApi.getProductosAfectados(selectedIngId!),
    enabled: !!selectedIngId,
  });
  const afectados = afectadosData ?? [];

  // Fetch measurement units for the dropdown, filtered by tipo when locked
  useEffect(() => {
    unidadesMedidaApi.getAll(unidadTipoFilter ?? undefined).then(setUnidades).catch(() => {});
  }, [unidadTipoFilter]);

  // ── TanStack Query ──
  const { data, isLoading, isError, error } = useIngredientes(skip, limit, debouncedSearch || undefined);
  const items = data?.items ?? [];
  const total = data?.total ?? 0;

  // Client-side sort
  const sortedItems = useMemo(() => {
    if (!sortBy) return items;
    return [...items].sort((a, b) => {
      const aVal = (a as unknown as Record<string, unknown>)[sortBy];
      const bVal = (b as unknown as Record<string, unknown>)[sortBy];
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortOrder === "asc" ? aVal - bVal : bVal - aVal;
      }
      const aStr = String(aVal ?? "");
      const bStr = String(bVal ?? "");
      return sortOrder === "asc" ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
    });
  }, [items, sortBy, sortOrder]);

  const createMutation = useCreateIngrediente();
  const updateMutation = useUpdateIngrediente();
  const deleteMutation = useDeleteIngrediente();

  // Auto-clear error after 3 seconds
  useEffect(() => {
    if (isError && error) {
      const timer = setTimeout(() => {}, 3000);
      return () => clearTimeout(timer);
    }
  }, [isError, error]);

  const form = useAppForm<IngredienteCreate>({
    defaultValues: { nombre: "", descripcion: "", es_alergeno: true, precio_actual: 0, stock_actual: 0, unidad_medida_id: 5 },
    onSubmit: async ({ value }: { value: IngredienteCreate }) => {
      try {
        if (editingId) {
          await updateMutation.mutateAsync({ id: editingId, data: value });
        } else {
          await createMutation.mutateAsync(value);
        }
        addToast('exito', 'Insumo guardado correctamente');
        handleCloseForm();
      } catch (err) {
        const parsed = parseApiError(err);
        if (parsed.validationErrors.length > 0) {
          parsed.validationErrors.forEach((m) => addToast('error', m));
          return;
        }
        const msg = parsed.detail || 'Error del servidor';
        addToast('error', msg);
      }
    },
  });

  // ── Auto-populate form from query param ?edit=<id> (e.g. from stock modal) ──
  useEffect(() => {
    if (!queryEditId || queryEditTriggered.current) return;
    if (unidades.length === 0 || items.length === 0) return;
    const ing = items.find((i) => i.id === queryEditId);
    if (ing) {
      queryEditTriggered.current = true;
      // Use the exact same code path as the Edit button click
      prevUnidadMedidaIdRef.current = null;
      form.setFieldValue("nombre", ing.nombre);
      form.setFieldValue("descripcion", ing.descripcion ?? "");
      form.setFieldValue("unidad_medida_id", ing.unidad_medida_id ?? null);
      form.setFieldValue("es_alergeno", ing.es_alergeno);
      form.setFieldValue("precio_actual", ing.precio_actual);
      form.setFieldValue("stock_actual", ing.stock_actual);
      setEditingId(ing.id);
      setShowForm(true);
      if (ing.unidad_medida_id) {
        const fromState = unidades.find(u => u.id === ing.unidad_medida_id);
        if (fromState?.tipo) setUnidadTipoFilter(fromState.tipo);
      }
      return;
    }
    // Not in current page — fetch directly
    queryEditTriggered.current = true;
    ingredientesApi.getById(queryEditId).then((fetched) => {
      prevUnidadMedidaIdRef.current = null;
      form.setFieldValue("nombre", fetched.nombre);
      form.setFieldValue("descripcion", fetched.descripcion ?? "");
      form.setFieldValue("unidad_medida_id", fetched.unidad_medida_id ?? null);
      form.setFieldValue("es_alergeno", fetched.es_alergeno);
      form.setFieldValue("precio_actual", fetched.precio_actual);
      form.setFieldValue("stock_actual", fetched.stock_actual);
      setEditingId(fetched.id);
      setShowForm(true);
      if (fetched.unidad_medida_id) {
        const fromState = unidades.find(u => u.id === fetched.unidad_medida_id);
        if (fromState?.tipo) setUnidadTipoFilter(fromState.tipo);
      }
    }).catch(() => {
      queryEditTriggered.current = false; // allow retry
      addToast("error", "No se pudo cargar el ingrediente. Verifica que exista.");
    });
  }, [queryEditId, items, unidades]);

  // ── Price/stock conversion when unidad_medida_id changes ──
  const watchedUnidadMedidaId = useStore(
    form.store,
    (state) => state.values.unidad_medida_id ?? null
  );

  // ── Dynamic price label based on selected unit ──
  const precioLabel = useMemo(() => {
    if (watchedUnidadMedidaId === null) return "Precio";
    const unit = unidades.find(u => u.id === watchedUnidadMedidaId);
    return unit ? `Precio por ${unit.nombre}` : "Precio";
  }, [watchedUnidadMedidaId, unidades]);

  useEffect(() => {
    // Read the LIVE value from the form store, not the render-captured
    // `watchedUnidadMedidaId`. When this effect runs in the SAME render cycle
    // as the ?edit= auto-populate effect, `watchedUnidadMedidaId` still holds
    // the stale default unit (porcion = 5), which would snapshot prev=5 and
    // later trigger a bogus price conversion (e.g. porcion -> kg, x1000) on the
    // next render. Reading the store directly yields the unit just set.
    const currentId = form.getFieldValue("unidad_medida_id") ?? null;

    // Tipo-locking: when editing, filter dropdown to same-tipo units after selection.
    // During creation, keep all tipos visible so the user can freely choose.
    if (currentId !== null && unidades.length > 0) {
      const selectedUnit = unidades.find(u => u.id === currentId);
      if (selectedUnit?.tipo && editingId) {
        setUnidadTipoFilter(selectedUnit.tipo);
      }
    }

    // First render: just track the current ID, no conversion
    if (prevUnidadMedidaIdRef.current === null) {
      prevUnidadMedidaIdRef.current = currentId;
      return;
    }

    // Guard: same unit (no-op) or null previous/current
    if (currentId === prevUnidadMedidaIdRef.current) return;
    if (currentId === null || prevUnidadMedidaIdRef.current === null) return;

    // Look up both units in the loaded unidades array
    const oldUnit = unidades.find(
      (u) => u.id === prevUnidadMedidaIdRef.current
    );
    const newUnit = unidades.find((u) => u.id === currentId);

    // Guard: both units must exist and have positive conversion factors
    if (!oldUnit?.factor_conversion || !newUnit?.factor_conversion) return;
    if (oldUnit.factor_conversion <= 0 || newUnit.factor_conversion <= 0) return;

    const oldFactor = Number(oldUnit.factor_conversion);
    const newFactor = Number(newUnit.factor_conversion);

    // Price conversion: newPrice = oldPrice * newFactor / oldFactor
    // (price is PER unit — smaller unit = smaller price)
    const convertPrice = (oldPrice: number) =>
      Math.round((oldPrice * newFactor / oldFactor) * 100) / 100;

    const oldPrecioActual = form.getFieldValue("precio_actual") ?? 0;
    form.setFieldValue("precio_actual", convertPrice(Number(oldPrecioActual)));

    // Stock conversion: newStock = oldStock * oldFactor / newFactor
    // (stock is total quantity — smaller unit = larger number of units)
    const oldStock = form.getFieldValue("stock_actual") ?? 0;
    form.setFieldValue(
      "stock_actual",
      Math.round(Number(oldStock) * oldFactor / newFactor)
    );

    // Track new unit as "old" for next change
    prevUnidadMedidaIdRef.current = currentId;
  }, [watchedUnidadMedidaId, unidades]);

  const handleStartCreate = () => {
    prevUnidadMedidaIdRef.current = null;
    setUnidadTipoFilter(null); // Show all units on create
    form.reset();
    setEditingId(null);
    setShowForm(true);
  };

  const handleStartEdit = (ing: Ingrediente) => {
    prevUnidadMedidaIdRef.current = null;
    form.setFieldValue("nombre", ing.nombre);
    form.setFieldValue("descripcion", ing.descripcion ?? "");
    form.setFieldValue("unidad_medida_id", ing.unidad_medida_id ?? null);
    form.setFieldValue("es_alergeno", ing.es_alergeno);
    form.setFieldValue("precio_actual", ing.precio_actual);
    form.setFieldValue("stock_actual", ing.stock_actual);
    setEditingId(ing.id);
    setShowForm(true);

    // Detect tipo from ingredient's current unit to pre-filter dropdown
    if (ing.unidad_medida_id) {
      const fromState = unidades.find(u => u.id === ing.unidad_medida_id);
      if (fromState?.tipo) {
        setUnidadTipoFilter(fromState.tipo);
      } else {
        // unidades might be stale/empty — fetch all to find tipo
        unidadesMedidaApi.getAll().then(all => {
          const u = all.find(x => x.id === ing.unidad_medida_id);
          setUnidadTipoFilter(u?.tipo ?? null);
        }).catch(() => {});
      }
    }
  };

  const handleCloseForm = () => {
    prevUnidadMedidaIdRef.current = null;
    setUnidadTipoFilter(null); // Reset filter so all units load again
    form.reset();
    setShowForm(false);
    setEditingId(null);
  };

  const handleExport = async () => {
    try {
      const allData = await ingredientesApi.getAll(0, 10000);
      const exportData = allData
        .filter((i) =>
          i.nombre.toLowerCase().includes(search.toLowerCase())
        )
        .map(({ id, nombre, es_alergeno, precio_actual, stock_actual }) => ({
          id,
          nombre,
          "Es alergeno?": es_alergeno ? "Si" : "No",
          Precio: formatCurrency(precio_actual),
          Stock: stock_actual,
        }));

      if (exportData.length === 0) {
        addToast('error', "No hay ingredientes para exportar");
        return;
      }
      exportToExcel(exportData, "ingredientes");
    } catch (e) {
      addToast('error', "Error al exportar: " + (e as Error).message);
    }
  };

  const handleDelete = (id: number) => {
    const ing = items.find(i => i.id === id);
    crud.openDeleteConfirm(id, ing?.nombre ?? `#${id}`);
  };

  const handleConfirmDelete = async () => {
    if (!crud.deleteTarget) return;
    try {
      await deleteMutation.mutateAsync(crud.deleteTarget.id);
      addToast('exito', 'Insumo eliminado');
    } catch (err) {
      addToast('error', (err as Error).message);
    } finally {
      crud.closeDeleteConfirm();
    }
  };

  const columns: DataTableColumn<Ingrediente>[] = [
    ...(showId ? [{
      key: "id" as const,
      label: "Codigo",
      sortable: true,
      hideOnMobile: true,
      render: (ing: Ingrediente) => <span className="text-gray-500 text-xs">#{ing.id}</span>,
    }] : []),
    {
      key: "nombre",
      label: "Nombre",
      render: (ing) => (
        <span className="flex items-center gap-2">
          {ing.nombre}
          {ing.unidad_medida_simbolo && (
            <span className="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
              {ing.unidad_medida_simbolo}
            </span>
          )}
        </span>
      ),
    },
    {
      key: "descripcion",
      label: "Descripcion",
      render: (ing) => ing.descripcion ?? "—",
      hideOnMobile: true,
    },
    {
      key: "es_alergeno",
      label: "Alergeno?",
      render: (ing) => (ing.es_alergeno ? "Si" : "No"),
      hideOnMobile: true,
    },
    {
      key: "precio_actual",
      label: "Precio",
      sortable: true,
      render: (ing) => formatCurrency(ing.precio_actual),
    },
    {
      key: "stock_actual",
      label: "Stock",
      sortable: true,
      render: (ing) => <span>{ing.stock_actual}</span>,
    },
    {
      key: "acciones",
      label: "Acciones",
      render: (ing) => (
        <div className="flex gap-1 flex-wrap">
          <EditButton onClick={() => handleStartEdit(ing)} />
          <DeleteButton onClick={() => handleDelete(ing.id)} />
          <button
            onClick={() => setSelectedIngId(selectedIngId === ing.id ? null : ing.id)}
            className={`px-2 py-1 rounded text-xs cursor-pointer transition-colors ${selectedIngId === ing.id ? "bg-amber-600 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
          >
            {selectedIngId === ing.id ? "Ocultar productos" : "Ver productos"}
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Ingredientes</h1>
      <ErrorBanner isError={isError} error={error} message="Error al cargar" />
      <CrudToolbar
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Filtrar por nombre..."
        onCreateClick={handleStartCreate}
        createLabel="+ Nuevo"
        onExportClick={handleExport}
        exportLabel="Exportar Excel"
      />
      <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="border p-4 mb-4 rounded bg-gray-50 flex gap-4 items-end flex-wrap" style={{ display: showForm ? '' : 'none' }}>
          <div>
            <form.Field name="nombre" validators={{
              onChange: ({ value }) => {
                if (!value || (typeof value === 'string' && value.trim() === '')) return 'El nombre es obligatorio';
                if (typeof value === 'string' && value.length > 100) return 'Maximo 100 caracteres';
                return undefined;
              }
            }}>
              {(field) => (
                <>
                  <label className="block text-sm font-medium">Nombre</label>
                  <input value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    className="border px-2 py-1 rounded" required />
                  {field.state.meta.errors && (
                    <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                  )}
                </>
              )}
            </form.Field>
          </div>
          <div>
            <form.Field name="descripcion">
              {(field) => (
                <>
                  <label className="block text-sm font-medium">Descripcion</label>
                  <input value={field.state.value ?? ""}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    className="border px-2 py-1 rounded w-48" />
                  {field.state.meta.errors && (
                    <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                  )}
                </>
              )}
            </form.Field>
          </div>
          <div>
            <form.Field name="unidad_medida_id">
              {(field) => (
                <>
                  <label className="block text-sm font-medium">Unidad <span className="text-red-500">*</span></label>
                  <select
                    value={field.state.value ?? ""}
                    onChange={(e) => field.handleChange(e.target.value ? Number(e.target.value) : null)}
                    onBlur={field.handleBlur}
                    className="border px-1 py-1 rounded text-sm"
                  >
                    <option value="5">Porcion</option>
                    {unidades.filter(u => u.id !== 5).map((u) => (
                      <option key={u.id} value={u.id}>{u.simbolo} ({u.nombre})</option>
                    ))}
                  </select>
                  {field.state.value == null && (
                    <p className="text-red-500 text-sm mt-1">La unidad es obligatoria</p>
                  )}
                </>
              )}
            </form.Field>
          </div>
          <div>
            <form.Field name="precio_actual" validators={{
              onChange: ({ value }) => {
                if (value != null && value < 0) return 'Debe ser mayor o igual a 0';
                if (value != null && value > 999999.99) return 'Debe ser menor o igual a 999999.99';
                return undefined;
              }
            }}>
              {(field) => (
                <>
                  <label className="block text-sm font-medium">{precioLabel}</label>
                  <DecimalInput
                    value={field.state.value ?? 0}
                    onChange={(v) => field.handleChange(v)}
                    onBlur={field.handleBlur}
                    decimals={2}
                    min={0}
                    step={0.01}
                    isCurrency
                    width="min-w-[10ch]"
                  />
                  {/* Hint: total stock value = unit price x stock quantity */}
                  {(() => {
                    const precio = form.getFieldValue('precio_actual');
                    const stock = form.getFieldValue('stock_actual');
                    if (precio != null && stock != null && Number(precio) > 0 && Number(stock) > 0) {
                      return (
                        <p className="text-xs text-gray-400 mt-1">
                          Valor total del stock: {formatCurrency(Number(precio) * Number(stock))}
                        </p>
                      );
                    }
                    return null;
                  })()}
                  {field.state.meta.errors && (
                    <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                  )}
                </>
              )}
            </form.Field>
          </div>
          <div>
            <form.Field name="stock_actual" validators={{
              onChange: ({ value }) => {
                if (value != null && value < 0) return 'Debe ser mayor o igual a 0';
                if (value != null && !Number.isInteger(Number(value))) return 'Debe ser un numero entero';
                return undefined;
              }
            }}>
              {(field) => (
                <>
                  <label className="block text-sm font-medium">Stock actual</label>
                  <DecimalInput
                    value={field.state.value ?? 0}
                    onChange={(v) => field.handleChange(v)}
                    onBlur={field.handleBlur}
                    decimals={0}
                    min={0}
                    step={1}
                    width="min-w-[8ch]"
                  />
                  {field.state.meta.errors && (
                    <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                  )}
                </>
              )}
            </form.Field>
          </div>
          <div className="flex items-center gap-2">
            <form.Field name="es_alergeno">
              {(field) => (
                <>
                  <label className="text-sm font-medium">Es alergeno?</label>
                  <input type="checkbox" checked={field.state.value ?? true}
                    onChange={(e) => field.handleChange(e.target.checked)} />
                  {field.state.meta.errors && (
                    <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
                  )}
                </>
              )}
            </form.Field>
          </div>
          <FormFooter
            isSubmitting={false}
            isEditing={!!editingId}
            onCancel={handleCloseForm}
          />
        </form>

      {/* Stock Historial — shown when editing an ingredient */}
      {editingId && (
        <div className="mb-6 border rounded-lg p-4 bg-gray-50">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Historial de Stock</h3>
          <StockHistorialTab entidadTipo="ingrediente" entidadId={editingId} />
        </div>
      )}

      {/* Affected products — shown when an ingredient row is selected */}
      {selectedIngId && (
        <div className="mb-6 border rounded-lg p-4 bg-blue-50">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Productos que usan este ingrediente
          </h3>
          {afectados.length === 0 ? (
            <p className="text-sm text-gray-500 italic">
              Ningun producto usa este ingrediente actualmente.
            </p>
          ) : (
            <table className="w-full border-collapse border text-sm">
              <thead>
                <tr className="bg-blue-100">
                  <th className="border p-2 text-left">Producto</th>
                  <th className="border p-2 text-right">Stock derivado</th>
                  <th className="border p-2 text-center">Tipo</th>
                </tr>
              </thead>
              <tbody>
                {afectados.map((p) => (
                  <tr key={p.id} className="bg-white">
                    <td className="border p-2 font-medium">{p.nombre}</td>
                    <td className="border p-2 text-right font-mono">
                      {p.es_producto_terminado ? (
                        <span className="text-amber-700">
                          {p.stock_manual ?? 0}
                          <span className="text-xs text-amber-500 ml-1">(stock manual)</span>
                        </span>
                      ) : (
                        <span className={p.stock_derivado === 0 ? "text-red-600" : "text-green-700"}>
                          {p.stock_derivado}
                        </span>
                      )}
                    </td>
                    <td className="border p-2 text-center text-xs">
                      {p.es_producto_terminado ? (
                        <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-700">
                          Prod. terminado
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                          Fabricado
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      <DataTable
        columns={columns}
        data={sortedItems}
        total={total}
        skip={skip}
        limit={limit}
        onPageChange={handlePageChange}
        onLimitChange={handleLimitChange}
        isLoading={isLoading}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onSort={handleSort}
      />

      {/* ── Delete confirmation dialog ── */}
      <ConfirmDialog
        open={crud.deleteConfirmOpen}
        title="Eliminar ingrediente"
        message={`¿Esta seguro de eliminar '${crud.deleteTarget?.label ?? ''}'?`}
        variant="danger"
        confirmLabel="Eliminar"
        onConfirm={handleConfirmDelete}
        onCancel={crud.closeDeleteConfirm}
        isLoading={deleteMutation.isPending}
      />
    </div>
  );
}
