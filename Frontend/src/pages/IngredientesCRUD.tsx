import { useReducer, useEffect, useCallback } from "react";
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
  | { type: "UPDATE_FORM"; payload: Partial<IngredienteCreate> };

const emptyForm: IngredienteCreate = { nombre: "", es_alergeno: true };

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
        },
      };
    case "START_CREATE":
      return { ...state, editingId: null, showForm: true, form: emptyForm };
    case "CLOSE_FORM":
      return { ...state, showForm: false, editingId: null, form: emptyForm };
    case "UPDATE_FORM":
      return { ...state, form: { ...state.form, ...action.payload } };
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
      dispatch({ type: "SET_ERROR", payload: (err as Error).message });
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
        <button onClick={() => exportToExcel(filtered.map(({ id, nombre, es_alergeno }) => ({
            id, nombre, es_alergeno: es_alergeno ? "Sí" : "No",
          })), "ingredientes")}
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
            <th className="border p-2 text-left">Acciones</th>
          </tr></thead>
          <tbody>
            {filtered.map((ing) => (
              <tr key={ing.id} className="hover:bg-gray-100">
                <td className="border p-2">{ing.id}</td>
                <td className="border p-2">{ing.nombre}</td>
                <td className="border p-2">{ing.es_alergeno ? "Sí" : "No"}</td>
                <td className="border p-2 flex gap-1">
                  <button onClick={() => dispatch({ type: "START_EDIT", payload: ing })}
                    className="bg-yellow-500 text-white px-2 py-1 rounded text-sm cursor-pointer">Editar</button>
                  <button onClick={() => handleDelete(ing.id)}
                    className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Eliminar</button>
                </td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={4} className="border p-2 text-center text-gray-500">Sin resultados</td></tr>}
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
