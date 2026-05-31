import { useReducer, useEffect, useCallback } from "react";
import { AxiosError } from "axios";
import type { Ingrediente, IngredienteCreate } from "../api/ingredientes";
import { ingredientesApi } from "../api/ingredientes";
import { exportToExcel } from "../utils/exportExcel";

const PAGE_SIZE = 10;

interface State {
  items: Ingrediente[];
  loading: boolean;
  error: string | null;
  page: number;
  filter: string;
  editingId: number | null;
  showForm: boolean;
  form: IngredienteCreate;
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
  | { type: "UPDATE_FORM"; payload: Partial<IngredienteCreate> }
  | { type: "START_INLINE_STOCK"; payload: { id: number; currentValue: number } }
  | { type: "SET_INLINE_STOCK_VALUE"; payload: string }
  | { type: "CANCEL_INLINE_STOCK" }
  | { type: "START_INLINE_PRECIO"; payload: { id: number; currentValue: number } }
  | { type: "SET_INLINE_PRECIO_VALUE"; payload: string }
  | { type: "CANCEL_INLINE_PRECIO" };

const emptyForm: IngredienteCreate = { nombre: "", es_alergeno: true, precio_actual: 0, stock_actual: 0 };

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
      return { ...state, filter: action.payload, page: 0 };
    case "START_EDIT":
      return {
        ...state,
        editingId: action.payload.id,
        showForm: true,
        form: {
          nombre: action.payload.nombre,
          es_alergeno: action.payload.es_alergeno,
          precio_actual: action.payload.precio_actual,
          stock_actual: action.payload.stock_actual,
        },
      };
    case "START_CREATE":
      return { ...state, editingId: null, showForm: true, form: emptyForm };
    case "CLOSE_FORM":
      return { ...state, showForm: false, editingId: null, form: emptyForm, inlineStockEdit: null, inlinePrecioEdit: null };
    case "UPDATE_FORM":
      return { ...state, form: { ...state.form, ...action.payload } };
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
  form: emptyForm,
  inlineStockEdit: null,
  inlinePrecioEdit: null,
};

export default function IngredientesCRUD() {
  const [state, dispatch] = useReducer(reducer, init);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (state.editingId) {
        await ingredientesApi.update(state.editingId, state.form);
      } else {
        await ingredientesApi.create(state.form);
      }
      dispatch({ type: "CLOSE_FORM" });
      fetchData();
    } catch (err) {
      const msg = err instanceof AxiosError && err.response?.data
        ? (err.response.data as { detail?: string }).detail ?? (err as Error).message
        : (err as Error).message;
      dispatch({ type: "SET_ERROR", payload: msg });
    }
  };

  const handleExport = async () => {
    try {
      // Fetch ALL ingredients (no pagination) for export
      const allData = await ingredientesApi.getAll(0, 10000);

      // Apply current filter
      const exportData = allData
        .filter((i) =>
          i.nombre.toLowerCase().includes(state.filter.toLowerCase())
        )
        .map(({ id, nombre, es_alergeno, precio_actual, stock_actual }) => ({
          id,
          nombre,
          es_alergeno: es_alergeno ? "Sí" : "No",
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

  const handleDelete = async (id: number) => {
    if (!confirm("¿Eliminar este ingrediente?")) return;
    try {
      await ingredientesApi.delete(id);
      fetchData();
    } catch (err) {
      dispatch({ type: "SET_ERROR", payload: (err as Error).message });
    }
  };

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

  const filtered = state.items.filter((i) =>
    i.nombre.toLowerCase().includes(state.filter.toLowerCase())
  );

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Ingredientes</h1>
      {state.error && <div className="bg-red-100 text-red-700 p-2 mb-4 rounded">{state.error}</div>}
      <div className="flex gap-2 mb-4 flex-wrap">
        <input type="text" placeholder="Filtrar por nombre..." value={state.filter}
          onChange={(e) => dispatch({ type: "SET_FILTER", payload: e.target.value })}
          className="border px-3 py-1 rounded" />
        <button onClick={() => dispatch({ type: "START_CREATE" })}
          className="bg-green-600 text-white px-4 py-1 rounded cursor-pointer">+ Nuevo</button>
        <button onClick={handleExport}
          className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Exportar Excel</button>
      </div>
      {state.showForm && (
        <form onSubmit={handleSubmit} className="border p-4 mb-4 rounded bg-gray-50 flex gap-4 items-end flex-wrap">
          <div>
            <label className="block text-sm font-medium">Nombre</label>
            <input value={state.form.nombre}
              onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { nombre: e.target.value } })}
              className="border px-2 py-1 rounded" required />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">¿Es alérgeno?</label>
            <input type="checkbox" checked={state.form.es_alergeno ?? true}
              onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { es_alergeno: e.target.checked } })} />
          </div>
          <div>
            <label className="block text-sm font-medium">Precio</label>
            <input type="number" step="0.01" min="0" value={state.form.precio_actual ?? 0}
              onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { precio_actual: parseFloat(e.target.value) || 0 } })}
              className="border px-2 py-1 rounded w-28" />
          </div>
          <div>
            <label className="block text-sm font-medium">Stock</label>
            <input type="number" step="1" min="0" value={state.form.stock_actual ?? 0}
              onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { stock_actual: parseInt(e.target.value) || 0 } })}
              className="border px-2 py-1 rounded w-28" />
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">
            {state.editingId ? "Actualizar" : "Crear"}</button>
          <button type="button" onClick={() => dispatch({ type: "CLOSE_FORM" })}
            className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer">Cancelar</button>
        </form>
      )}
      {state.loading ? <p>Cargando...</p> : (
        <table className="w-full border-collapse border">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">ID</th>
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Alérgeno</th>
            <th className="border p-2 text-left">Precio</th>
            <th className="border p-2 text-left">Stock</th>
            <th className="border p-2 text-left">Acciones</th>
          </tr></thead>
          <tbody>
            {filtered.map((ing) => (
              <tr key={ing.id} className="hover:bg-gray-100">
                <td className="border p-2">{ing.id}</td>
                <td className="border p-2">{ing.nombre}</td>
                <td className="border p-2">{ing.es_alergeno ? "Sí" : "No"}</td>
                <td className="border p-2">
                  {state.inlinePrecioEdit?.id === ing.id ? (
                    <div className="flex gap-1 items-center">
                      <input type="number" step="0.01" min="0"
                        value={state.inlinePrecioEdit.value}
                        onChange={(e) => dispatch({ type: "SET_INLINE_PRECIO_VALUE", payload: e.target.value })}
                        className="border px-1 py-0.5 w-20 rounded text-sm" />
                      <button onClick={() => handleInlinePrecioSave(ing.id)}
                        className="bg-green-600 text-white px-2 py-0.5 rounded text-xs cursor-pointer">Guardar</button>
                      <button onClick={() => dispatch({ type: "CANCEL_INLINE_PRECIO" })}
                        className="bg-gray-400 text-white px-2 py-0.5 rounded text-xs cursor-pointer">✕</button>
                    </div>
                  ) : (
                    `$${Number(ing.precio_actual).toFixed(2)}`
                  )}
                </td>
                <td className="border p-2">
                  {state.inlineStockEdit?.id === ing.id ? (
                    <div className="flex gap-1 items-center">
                      <input type="number" step="1" min="0"
                        value={state.inlineStockEdit.value}
                        onChange={(e) => dispatch({ type: "SET_INLINE_STOCK_VALUE", payload: e.target.value })}
                        className="border px-1 py-0.5 w-20 rounded text-sm" />
                      <button onClick={() => handleInlineStockSave(ing.id)}
                        className="bg-green-600 text-white px-2 py-0.5 rounded text-xs cursor-pointer">Guardar</button>
                      <button onClick={() => dispatch({ type: "CANCEL_INLINE_STOCK" })}
                        className="bg-gray-400 text-white px-2 py-0.5 rounded text-xs cursor-pointer">✕</button>
                    </div>
                  ) : (
                    ing.stock_actual
                  )}
                </td>
                <td className="border p-2">
                  <div className="flex gap-1 flex-wrap">
                    <button onClick={() => dispatch({ type: "START_EDIT", payload: ing })}
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
      <div className="flex gap-2 mt-4 items-center">
        <button disabled={state.page === 0}
          onClick={() => dispatch({ type: "SET_PAGE", payload: state.page - 1 })}
          className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer">← Anterior</button>
        <span>Página {state.page + 1}</span>
        <button disabled={state.items.length < PAGE_SIZE}
          onClick={() => dispatch({ type: "SET_PAGE", payload: state.page + 1 })}
          className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer">Siguiente →</button>
      </div>
    </div>
  );
}
