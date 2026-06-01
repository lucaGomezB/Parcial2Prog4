/**
 * IngredientesCRUD — Ingredients (insumos) management admin page.
 *
 * Features:
 *   - Paginated list with client-side text filter.
 *   - CRUD: create, edit, delete ingredients.
 *   - Inline editing for stock (column click -> input).
 *   - Inline editing for price (column click -> input).
 *   - Allergen toggle (es_alergeno) via the create/edit form.
 *   - Excel export of filtered or full data.
 *
 * State management: useReducer for the data grid, TanStack Form for create/edit.
 */

import { useReducer, useEffect, useCallback } from "react";
import { AxiosError } from "axios";
import type { Ingrediente, IngredienteCreate } from "../api/ingredientes";
import { ingredientesApi } from "../api/ingredientes";
import { exportToExcel } from "../utils/exportExcel";
import { useAppForm, required } from "../hooks/useAppForm";

const PAGE_SIZE = 10;

/** All state for the data grid and inline editing. */
interface State {
  items: Ingrediente[];
  loading: boolean;
  error: string | null;
  page: number;
  filter: string;
  editingId: number | null;
  showForm: boolean;
  inlineStockEdit: { id: number; value: string } | null;
  inlinePrecioEdit: { id: number; value: string } | null;
}

type Action =
  | { type: "SET_ITEMS"; payload: Ingrediente[] }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string | null }
  | { type: "SET_PAGE"; payload: number }
  | { type: "SET_FILTER"; payload: string }
  | { type: "START_EDIT"; payload: Ingrediente }
  | { type: "START_CREATE" }
  | { type: "CLOSE_FORM" }
  | { type: "START_INLINE_STOCK"; payload: { id: number; currentValue: number } }
  | { type: "SET_INLINE_STOCK_VALUE"; payload: string }
  | { type: "CANCEL_INLINE_STOCK" }
  | { type: "START_INLINE_PRECIO"; payload: { id: number; currentValue: number } }
  | { type: "SET_INLINE_PRECIO_VALUE"; payload: string }
  | { type: "CANCEL_INLINE_PRECIO" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_ITEMS":
      return { ...state, items: action.payload, loading: false };
    case "SET_LOADING":
      return { ...state, loading: action.payload };
    case "SET_ERROR":
      return { ...state, error: action.payload, loading: false };
    case "SET_PAGE":
      return { ...state, page: action.payload };
    case "SET_FILTER":
      // Reset to first page when filter changes
      return { ...state, filter: action.payload, page: 0 };
    case "START_EDIT":
      return { ...state, editingId: action.payload.id, showForm: true };
    case "START_CREATE":
      return { ...state, editingId: null, showForm: true };
    case "CLOSE_FORM":
      return { ...state, showForm: false, editingId: null, inlineStockEdit: null, inlinePrecioEdit: null };
    case "START_INLINE_STOCK":
      return { ...state, inlineStockEdit: { id: action.payload.id, value: String(action.payload.currentValue) }, inlinePrecioEdit: null };
    case "SET_INLINE_STOCK_VALUE":
      return { ...state, inlineStockEdit: state.inlineStockEdit ? { ...state.inlineStockEdit, value: action.payload } : null };
    case "CANCEL_INLINE_STOCK":
      return { ...state, inlineStockEdit: null };
    case "START_INLINE_PRECIO":
      return { ...state, inlinePrecioEdit: { id: action.payload.id, value: String(action.payload.currentValue) }, inlineStockEdit: null };
    case "SET_INLINE_PRECIO_VALUE":
      return { ...state, inlinePrecioEdit: state.inlinePrecioEdit ? { ...state.inlinePrecioEdit, value: action.payload } : null };
    case "CANCEL_INLINE_PRECIO":
      return { ...state, inlinePrecioEdit: null };
    default:
      return state;
  }
}

const init: State = {
  items: [],
  loading: false,
  error: null,
  page: 0,
  filter: "",
  editingId: null,
  showForm: false,
  inlineStockEdit: null,
  inlinePrecioEdit: null,
};

export default function IngredientesCRUD() {
  const [state, dispatch] = useReducer(reducer, init);

  /** Fetches the current page of ingredients from the backend. */
  const fetchData = useCallback(async () => {
    dispatch({ type: "SET_LOADING", payload: true });
    try {
      const data = await ingredientesApi.getAll(state.page * PAGE_SIZE, PAGE_SIZE);
      dispatch({ type: "SET_ITEMS", payload: data });
    } catch (e) {
      dispatch({ type: "SET_ERROR", payload: (e as Error).message });
    }
  }, [state.page]);

  useEffect(() => { fetchData(); }, [fetchData]);

  /**
   * TanStack Form for creating/editing an ingredient.
   * Fields: nombre, es_alergeno, precio_actual, stock_actual.
   */
  const form = useAppForm<IngredienteCreate>({
    defaultValues: { nombre: "", es_alergeno: true, precio_actual: 0, stock_actual: 0 },
    onSubmit: async ({ value }) => {
      try {
        if (state.editingId) {
          await ingredientesApi.update(state.editingId, value);
        } else {
          await ingredientesApi.create(value);
        }
        dispatch({ type: "CLOSE_FORM" });
        fetchData();
      } catch (err) {
        const msg = err instanceof AxiosError && err.response?.data
          ? (err.response.data as { detail?: string }).detail ?? (err as Error).message
          : (err as Error).message;
        dispatch({ type: "SET_ERROR", payload: msg });
      }
    },
  });

  /** Opens the create form with blank defaults. */
  const handleStartCreate = () => {
    form.reset();
    dispatch({ type: "START_CREATE" });
  };

  /** Opens the edit form pre-filled with the ingredient's current values. */
  const handleStartEdit = (ing: Ingrediente) => {
    form.setFieldValue("nombre", ing.nombre);
    form.setFieldValue("es_alergeno", ing.es_alergeno);
    form.setFieldValue("precio_actual", ing.precio_actual);
    form.setFieldValue("stock_actual", ing.stock_actual);
    dispatch({ type: "START_EDIT", payload: ing });
  };

  /** Closes the form and resets all editing state. */
  const handleCloseForm = () => {
    form.reset();
    dispatch({ type: "CLOSE_FORM" });
  };

  /**
   * Exports ingredients to Excel.
   * Fetches up to 10,000 records, applies the current filter client-side,
   * and exports only matching items.
   */
  const handleExport = async () => {
    try {
      const allData = await ingredientesApi.getAll(0, 10000);
      const exportData = allData
        .filter((i) =>
          i.nombre.toLowerCase().includes(state.filter.toLowerCase())
        )
        .map(({ id, nombre, es_alergeno, precio_actual, stock_actual }) => ({
          id,
          nombre,
          es_alergeno: es_alergeno ? "Si" : "No",
          precio_actual: `$${Number(precio_actual).toFixed(2)}`,
          stock_actual,
        }));

      if (exportData.length === 0) {
        dispatch({ type: "SET_ERROR", payload: "No hay ingredientes para exportar" });
        setTimeout(() => dispatch({ type: "SET_ERROR", payload: null }), 3000);
        return;
      }

      exportToExcel(exportData, "ingredientes");
    } catch (e) {
      dispatch({ type: "SET_ERROR", payload: "Error al exportar: " + (e as Error).message });
      setTimeout(() => dispatch({ type: "SET_ERROR", payload: null }), 3000);
    }
  };

  /** Deletes an ingredient after user confirmation. */
  const handleDelete = async (id: number) => {
    if (!confirm("Eliminar este ingrediente?")) return;
    try {
      await ingredientesApi.delete(id);
      fetchData();
    } catch (err) {
      dispatch({ type: "SET_ERROR", payload: (err as Error).message });
    }
  };

  /** Saves the inline stock edit value to the backend. */
  const handleInlineStockSave = async (id: number) => {
    if (!state.inlineStockEdit) return;
    const val = Number(state.inlineStockEdit.value);
    if (isNaN(val) || val < 0) return;
    try {
      await ingredientesApi.updateStock(id, val);
      dispatch({ type: "CANCEL_INLINE_STOCK" });
      fetchData();
    } catch (err) {
      dispatch({ type: "SET_ERROR", payload: (err as Error).message });
    }
  };

  /** Saves the inline price edit value to the backend. */
  const handleInlinePrecioSave = async (id: number) => {
    if (!state.inlinePrecioEdit) return;
    const val = Number(state.inlinePrecioEdit.value);
    if (isNaN(val) || val < 0) return;
    try {
      await ingredientesApi.updatePrecio(id, val);
      dispatch({ type: "CANCEL_INLINE_PRECIO" });
      fetchData();
    } catch (err) {
      dispatch({ type: "SET_ERROR", payload: (err as Error).message });
    }
  };

  // Client-side filter for the current page
  const filtered = state.items.filter((i) =>
    i.nombre.toLowerCase().includes(state.filter.toLowerCase())
  );

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Insumos</h1>
      {state.error && <div className="bg-red-100 text-red-700 p-2 mb-4 rounded">{state.error}</div>}
      {/* Toolbar: filter, create, export */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <input type="text" placeholder="Filtrar por nombre..." value={state.filter}
          onChange={(e) => dispatch({ type: "SET_FILTER", payload: e.target.value })}
          className="border px-3 py-1 rounded" />
        <button onClick={handleStartCreate}
          className="bg-green-600 text-white px-4 py-1 rounded cursor-pointer">+ Nuevo</button>
        <button onClick={handleExport}
          className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Exportar Excel</button>
      </div>
      {/* Inline create/edit form */}
      {state.showForm && (
        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="border p-4 mb-4 rounded bg-gray-50 flex gap-4 items-end flex-wrap">
          <div>
            <form.Field name="nombre" validators={{ onChange: required() }}>
              {(field) => (
                <>
                  <label className="block text-sm font-medium">Nombre</label>
                  <input value={field.state.value}
                    onChange={(e) => field.handleChange(e.target.value)}
                    onBlur={field.handleBlur}
                    className="border px-2 py-1 rounded" required />
                </>
              )}
            </form.Field>
          </div>
          {/* Allergen toggle checkbox — default true for new ingredients */}
          <div className="flex items-center gap-2">
            <form.Field name="es_alergeno">
              {(field) => (
                <>
                  <label className="text-sm font-medium">Es alergeno?</label>
                  <input type="checkbox" checked={field.state.value ?? true}
                    onChange={(e) => field.handleChange(e.target.checked)} />
                </>
              )}
            </form.Field>
          </div>
          <div>
            <form.Field name="precio_actual" validators={{ onChange: ({ value }) => value != null && value < 0 ? 'Debe ser mayor o igual a 0' : undefined }}>
              {(field) => (
                <>
                  <label className="block text-sm font-medium">Precio</label>
                  <input type="number" step="0.01" min="0" value={field.state.value}
                    onChange={(e) => field.handleChange(parseFloat(e.target.value) || 0)}
                    onBlur={field.handleBlur}
                    className="border px-2 py-1 rounded w-28" />
                </>
              )}
            </form.Field>
          </div>
          <div>
            <form.Field name="stock_actual" validators={{ onChange: ({ value }) => value != null && value < 0 ? 'Debe ser mayor o igual a 0' : undefined }}>
              {(field) => (
                <>
                  <label className="block text-sm font-medium">Stock</label>
                  <input type="number" step="1" min="0" value={field.state.value}
                    onChange={(e) => field.handleChange(parseInt(e.target.value) || 0)}
                    onBlur={field.handleBlur}
                    className="border px-2 py-1 rounded w-28" />
                </>
              )}
            </form.Field>
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">
            {state.editingId ? "Actualizar" : "Crear"}</button>
          <button type="button" onClick={handleCloseForm}
            className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer">Cancelar</button>
        </form>
      )}
      {/* Data table with inline stock/price editing */}
      {state.loading ? <p>Cargando...</p> : (
        <table className="w-full border-collapse border">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">ID</th>
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Alergeno</th>
            <th className="border p-2 text-left">Precio</th>
            <th className="border p-2 text-left">Stock</th>
            <th className="border p-2 text-left">Acciones</th>
          </tr></thead>
          <tbody>
            {filtered.map((ing) => (
              <tr key={ing.id} className="hover:bg-gray-100">
                <td className="border p-2">{ing.id}</td>
                <td className="border p-2">{ing.nombre}</td>
                <td className="border p-2">{ing.es_alergeno ? "Si" : "No"}</td>
                <td className="border p-2">
                  {/* Inline price editing: clicking "Precio" button replaces cell with input */}
                  {state.inlinePrecioEdit?.id === ing.id ? (
                    <div className="flex gap-1 items-center">
                      <input type="number" step="0.01" min="0"
                        value={state.inlinePrecioEdit.value}
                        onChange={(e) => dispatch({ type: "SET_INLINE_PRECIO_VALUE", payload: e.target.value })}
                        className="border px-1 py-0.5 w-20 rounded text-sm" />
                      <button onClick={() => handleInlinePrecioSave(ing.id)}
                        className="bg-green-600 text-white px-2 py-0.5 rounded text-xs cursor-pointer">Guardar</button>
                      <button onClick={() => dispatch({ type: "CANCEL_INLINE_PRECIO" })}
                        className="bg-gray-400 text-white px-2 py-0.5 rounded text-xs cursor-pointer">X</button>
                    </div>
                  ) : (
                    `$${Number(ing.precio_actual).toFixed(2)}`
                  )}
                </td>
                <td className="border p-2">
                  {/* Inline stock editing: clicking "Stock" button replaces cell with input */}
                  {state.inlineStockEdit?.id === ing.id ? (
                    <div className="flex gap-1 items-center">
                      <input type="number" step="1" min="0"
                        value={state.inlineStockEdit.value}
                        onChange={(e) => dispatch({ type: "SET_INLINE_STOCK_VALUE", payload: e.target.value })}
                        className="border px-1 py-0.5 w-20 rounded text-sm" />
                      <button onClick={() => handleInlineStockSave(ing.id)}
                        className="bg-green-600 text-white px-2 py-0.5 rounded text-xs cursor-pointer">Guardar</button>
                      <button onClick={() => dispatch({ type: "CANCEL_INLINE_STOCK" })}
                        className="bg-gray-400 text-white px-2 py-0.5 rounded text-xs cursor-pointer">X</button>
                    </div>
                  ) : (
                    ing.stock_actual
                  )}
                </td>
                <td className="border p-2">
                  <div className="flex gap-1 flex-wrap">
                    <button onClick={() => handleStartEdit(ing)}
                      className="bg-yellow-500 text-white px-2 py-1 rounded text-sm cursor-pointer">Editar</button>
                    <button onClick={() => dispatch({ type: "START_INLINE_STOCK", payload: { id: ing.id, currentValue: ing.stock_actual } })}
                      className="bg-teal-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Stock</button>
                    <button onClick={() => dispatch({ type: "START_INLINE_PRECIO", payload: { id: ing.id, currentValue: ing.precio_actual } })}
                      className="bg-purple-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Precio</button>
                    <button onClick={() => handleDelete(ing.id)}
                      className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Eliminar</button>
                  </div>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={6} className="border p-2 text-center text-gray-500">Sin resultados</td></tr>}
          </tbody>
        </table>
      )}
      {/* Pagination controls */}
      <div className="flex gap-2 mt-4 items-center">
        <button disabled={state.page === 0}
          onClick={() => dispatch({ type: "SET_PAGE", payload: state.page - 1 })}
          className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer">Anterior</button>
        <span>Pagina {state.page + 1}</span>
        <button disabled={state.items.length < PAGE_SIZE}
          onClick={() => dispatch({ type: "SET_PAGE", payload: state.page + 1 })}
          className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer">Siguiente</button>
      </div>
    </div>
  );
}
