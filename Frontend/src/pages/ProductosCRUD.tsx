import { useReducer, useEffect, useCallback, useState, useRef } from "react";
import type { Producto, ProductoCreate, ProductoIngredienteRead, ProductoCategoriaRead, ProductoMedida } from "../api/productos";
import { productosApi } from "../api/productos";
import type { Ingrediente } from "../api/ingredientes";
import { ingredientesApi } from "../api/ingredientes";
import type { Categoria } from "../api/categorias";
import { categoriasApi } from "../api/categorias";
import { useNavigate } from "react-router-dom";
import { exportToExcel } from "../utils/exportExcel";
import { addToCart, getItemCount } from "../utils/carrito";
import { AxiosError } from "axios";
import { getAccessToken } from "../api/client";

const PAGE_SIZE = 10;

interface State {
  items: Producto[];
  loading: boolean;
  error: string | null;
  page: number;
  filter: string;
  editingId: number | null;
  showForm: boolean;
  stockEditOnly: boolean;
  form: ProductoCreate;
  selectedCategorias: {id: number, nombre: string, descripcion: string | null}[];
  selectedIngredientes: {id: number, nombre: string, es_alergeno: boolean}[];
  showCategoriaSelector: boolean;
  showIngredienteSelector: boolean;
}

type Action =
  | { type: "SET_ITEMS"; payload: Producto[] }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string | null }
  | { type: "SET_PAGE"; payload: number }
  | { type: "SET_FILTER"; payload: string }
  | { type: "START_EDIT"; payload: Producto }
  | { type: "START_STOCK_EDIT"; payload: Producto }
  | { type: "START_CREATE" }
  | { type: "CLOSE_FORM" }
  | { type: "UPDATE_FORM"; payload: Partial<ProductoCreate> }
  | { type: "SET_SELECTED_CATEGORIAS"; payload: {id: number, nombre: string, descripcion: string | null}[] }
  | { type: "SET_SELECTED_INGREDIENTES"; payload: {id: number, nombre: string, es_alergeno: boolean}[] }
  | { type: "SET_SHOW_CATEGORIA_SELECTOR"; payload: boolean }
  | { type: "SET_SHOW_INGREDIENTE_SELECTOR"; payload: boolean };

const emptyForm: ProductoCreate = {
  nombre: "", descripcion: "", precio_base: 0, tiempo_prep_min: 0,
  disponible: true, stock_cantidad: 0, imagenes_url: [], categorias_ids: [], ingredientes: [], medidas: [],
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "SET_ITEMS": return { ...state, items: action.payload, loading: false };
    case "SET_LOADING": return { ...state, loading: action.payload };
    case "SET_ERROR": return { ...state, error: action.payload, loading: false };
    case "SET_PAGE": return { ...state, page: action.payload };
    case "SET_FILTER": return { ...state, filter: action.payload, page: 0 };
    case "START_EDIT":
      return {
        ...state, editingId: action.payload.id, showForm: true, stockEditOnly: false,
        form: {
          nombre: action.payload.nombre,
          descripcion: action.payload.descripcion ?? "",
          precio_base: action.payload.precio_base,
          stock_cantidad: action.payload.stock_cantidad,
          tiempo_prep_min: action.payload.tiempo_prep_min,
          disponible: action.payload.disponible,
          imagenes_url: action.payload.imagenes_url,
          medidas: (action.payload.medidas ?? []).map(m => ({
            nombre: m.nombre, precio: m.precio, stock: m.stock, orden: m.orden,
          })),
        },
        selectedCategorias: [],
        selectedIngredientes: [],
        showCategoriaSelector: false,
        showIngredienteSelector: false,
      };
    case "START_STOCK_EDIT":
      return {
        ...state, editingId: action.payload.id, showForm: true, stockEditOnly: true,
        form: {
          nombre: action.payload.nombre,
          descripcion: action.payload.descripcion ?? "",
          precio_base: action.payload.precio_base,
          stock_cantidad: action.payload.stock_cantidad,
          tiempo_prep_min: action.payload.tiempo_prep_min,
          disponible: action.payload.disponible,
          imagenes_url: action.payload.imagenes_url,
          medidas: (action.payload.medidas ?? []).map(m => ({
            nombre: m.nombre, precio: m.precio, stock: m.stock, orden: m.orden,
          })),
        },
        selectedCategorias: [],
        selectedIngredientes: [],
        showCategoriaSelector: false,
        showIngredienteSelector: false,
      };
    case "START_CREATE": return { ...state, editingId: null, showForm: true, stockEditOnly: false, form: emptyForm, selectedCategorias: [], selectedIngredientes: [], showCategoriaSelector: false, showIngredienteSelector: false };
    case "CLOSE_FORM": return { ...state, showForm: false, editingId: null, stockEditOnly: false, form: emptyForm, selectedCategorias: [], selectedIngredientes: [], showCategoriaSelector: false, showIngredienteSelector: false };
    case "UPDATE_FORM": return { ...state, form: { ...state.form, ...action.payload } };
    case "SET_SELECTED_CATEGORIAS": return { ...state, selectedCategorias: action.payload, form: { ...state.form, categorias_ids: action.payload.map(c => c.id) } };
    case "SET_SELECTED_INGREDIENTES": return { ...state, selectedIngredientes: action.payload, form: { ...state.form, ingredientes: action.payload.map(i => ({ ingrediente_id: i.id, es_removible: true, es_principal: false, orden: 0 })) } };
    case "SET_SHOW_CATEGORIA_SELECTOR": return { ...state, showCategoriaSelector: action.payload };
    case "SET_SHOW_INGREDIENTE_SELECTOR": return { ...state, showIngredienteSelector: action.payload };
    default: return state;
  }
}

const init: State = {
  items: [], loading: false, error: null, page: 0, filter: "",
  editingId: null, showForm: false, stockEditOnly: false, form: emptyForm,
  selectedCategorias: [], selectedIngredientes: [], showCategoriaSelector: false, showIngredienteSelector: false,
};

/* ── Selector de Categorías (para creación) ── */
function CategoriaSelector({ allCategorias, selectedIds, onSelect, onClose }: {
  allCategorias: Categoria[]; selectedIds: number[]; onSelect: (ids: number[]) => void; onClose: () => void;
}) {
  const [localSelected, setLocalSelected] = useState<number[]>(selectedIds);

  const toggleCategory = (id: number) => {
    setLocalSelected(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const handleConfirm = () => {
    onSelect(localSelected);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-2xl max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Seleccionar Categorías</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">✕</button>
        </div>
        <table className="w-full border-collapse border mb-4">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Seleccionar</th>
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Descripción</th>
          </tr></thead>
          <tbody>
            {allCategorias.map((cat) => (
              <tr key={cat.id}>
                <td className="border p-2">
                  <input type="checkbox" checked={localSelected.includes(cat.id)} onChange={() => toggleCategory(cat.id)} />
                </td>
                <td className="border p-2">{cat.nombre}</td>
                <td className="border p-2">{cat.descripcion ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex gap-2">
          <button onClick={handleConfirm} className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Confirmar</button>
          <button onClick={onClose} className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer">Cancelar</button>
        </div>
      </div>
    </div>
  );
}

/* ── Selector de Ingredientes (para creación) ── */
function IngredienteSelector({ allIngredientes, selectedIds, onSelect, onClose }: {
  allIngredientes: Ingrediente[]; selectedIds: number[]; onSelect: (ids: number[]) => void; onClose: () => void;
}) {
  const [localSelected, setLocalSelected] = useState<number[]>(selectedIds);

  const toggleIngredient = (id: number) => {
    setLocalSelected(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const handleConfirm = () => {
    onSelect(localSelected);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-2xl max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Seleccionar Ingredientes</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">✕</button>
        </div>
        <table className="w-full border-collapse border mb-4">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Seleccionar</th>
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Alérgeno</th>
          </tr></thead>
          <tbody>
            {allIngredientes.map((ing) => (
              <tr key={ing.id}>
                <td className="border p-2">
                  <input type="checkbox" checked={localSelected.includes(ing.id)} onChange={() => toggleIngredient(ing.id)} />
                </td>
                <td className="border p-2">{ing.nombre}</td>
                <td className="border p-2">{ing.es_alergeno ? "Sí" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="flex gap-2">
          <button onClick={handleConfirm} className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Confirmar</button>
          <button onClick={onClose} className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer">Cancelar</button>
        </div>
      </div>
    </div>
  );
}

/* ── Popup de Ingredientes ── */
function IngredientesPopup({ productoId, productoNombre, onClose }: {
  productoId: number; productoNombre: string; onClose: () => void;
}) {
  const [ings, setIngs] = useState<ProductoIngredienteRead[]>([]);
  const [allIngs, setAllIngs] = useState<Ingrediente[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<number | null>(null);
  const [addForm, setAddForm] = useState({ ingrediente_id: 0, es_removible: true, es_principal: false, orden: 0 });
  const [showAdd, setShowAdd] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const [prodIngs, available] = await Promise.all([
      productosApi.getIngredientes(productoId),
      ingredientesApi.getAll(0, 1000),
    ]);
    setIngs(prodIngs);
    setAllIngs(available);
    setLoading(false);
  }, [productoId]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    if (!addForm.ingrediente_id) return;
    await productosApi.addIngrediente(productoId, addForm);
    setShowAdd(false);
    setAddForm({ ingrediente_id: 0, es_removible: true, es_principal: false, orden: 0 });
    load();
  };

  const handleRemove = async (ingredienteId: number) => {
    if (!confirm("¿Quitar este ingrediente?")) return;
    await productosApi.removeIngrediente(productoId, ingredienteId);
    load();
  };

  const handleToggleAlergeno = async (ingredienteId: number, currentValue: boolean) => {
    setToggling(ingredienteId);
    try {
      await ingredientesApi.update(ingredienteId, { es_alergeno: !currentValue });
      await load(); // Recargar todo para reflejar cambios
    } catch {
      // Si no tiene permisos, el backend devuelve 403
    } finally {
      setToggling(null);
    }
  };

  // Helper: buscar info del ingrediente completo desde allIngs
  const getIngInfo = (ingredienteId: number) =>
    allIngs.find((i) => i.id === ingredienteId);

  // Filter out already-assigned ingredients
  const availableIngs = allIngs.filter(
    (ai) => !ings.some((i) => i.ingrediente_id === ai.id)
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-2xl max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Ingredientes de "{productoNombre}"</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">✕</button>
        </div>

        {loading ? <p>Cargando...</p> : (
          <>
            {ings.length === 0 ? (
              <p className="text-gray-500 mb-4">Sin ingredientes asignados.</p>
            ) : (
              <table className="w-full border-collapse border mb-4">
                <thead><tr className="bg-gray-200">
                  <th className="border p-2 text-left">Orden</th>
                  <th className="border p-2 text-left">Ingrediente</th>
                  <th className="border p-2 text-left">Alérgeno</th>
                  <th className="border p-2 text-left">Removible</th>
                  <th className="border p-2 text-left">Principal</th>
                  <th className="border p-2 text-left">Acciones</th>
                </tr></thead>
                <tbody>
                  {ings.map((ing) => {
                    const info = getIngInfo(ing.ingrediente_id);
                    const isAlergeno = info?.es_alergeno ?? false;
                    return (
                      <tr key={ing.ingrediente_id}>
                        <td className="border p-2">{ing.orden}</td>
                        <td className="border p-2">{ing.ingrediente_nombre}</td>
                        <td className="border p-2">
                          <span className="inline-flex items-center gap-1">
                            <span className={isAlergeno ? "text-red-600 font-medium" : "text-gray-500"}>
                              {isAlergeno ? "Sí" : "No"}
                            </span>
                            <button
                              onClick={() => handleToggleAlergeno(ing.ingrediente_id, isAlergeno)}
                              disabled={toggling === ing.ingrediente_id}
                              className="text-xs border border-gray-400 rounded px-1.5 py-0.5 hover:bg-gray-100 cursor-pointer disabled:opacity-50"
                              title={isAlergeno ? "Marcar como no alérgeno" : "Marcar como alérgeno"}
                            >
                              {toggling === ing.ingrediente_id ? "..." : "Cambiar"}
                            </button>
                          </span>
                        </td>
                        <td className="border p-2">{ing.es_removible ? "Sí" : "No"}</td>
                        <td className="border p-2">{ing.es_principal ? "Sí" : "No"}</td>
                        <td className="border p-2">
                          <button onClick={() => handleRemove(ing.ingrediente_id)}
                            className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-red-700">Quitar</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}

            {!showAdd ? (
              <button onClick={() => setShowAdd(true)}
                className="bg-green-600 text-white px-4 py-1 rounded cursor-pointer hover:bg-green-700">+ Agregar Ingrediente</button>
            ) : (
              <div className="border p-3 rounded bg-gray-50">
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <div>
                    <label className="block text-sm font-medium">Ingrediente</label>
                    <select value={addForm.ingrediente_id}
                      onChange={(e) => setAddForm({ ...addForm, ingrediente_id: Number(e.target.value) })}
                      className="border px-2 py-1 rounded w-full">
                      <option value={0}>-- Seleccionar --</option>
                      {availableIngs.map((ai) => (
                        <option key={ai.id} value={ai.id}>{ai.nombre}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium">Orden</label>
                    <input type="number" value={addForm.orden}
                      onChange={(e) => setAddForm({ ...addForm, orden: Number(e.target.value) })}
                      className="border px-2 py-1 rounded w-full" />
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm">Removible</label>
                    <input type="checkbox" checked={addForm.es_removible}
                      onChange={(e) => setAddForm({ ...addForm, es_removible: e.target.checked })} />
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm">Principal</label>
                    <input type="checkbox" checked={addForm.es_principal}
                      onChange={(e) => setAddForm({ ...addForm, es_principal: e.target.checked })} />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={handleAdd}
                    className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Confirmar</button>
                  <button onClick={() => setShowAdd(false)}
                    className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer">Cancelar</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* ── Popup de Categorías ── */
function CategoriasPopup({ productoId, productoNombre, onClose }: {
  productoId: number; productoNombre: string; onClose: () => void;
}) {
  const [cats, setCats] = useState<ProductoCategoriaRead[]>([]);
  const [allCats, setAllCats] = useState<Categoria[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ categoria_id: 0, es_principal: false });

  const load = useCallback(async () => {
    setLoading(true);
    const [prodCats, available] = await Promise.all([
      productosApi.getCategorias(productoId),
      categoriasApi.getAll(0, 1000),
    ]);
    setCats(prodCats);
    setAllCats(available);
    setLoading(false);
  }, [productoId]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    if (!addForm.categoria_id) return;
    try {
      await productosApi.addCategoria(productoId, addForm);
      setShowAdd(false);
      setAddForm({ categoria_id: 0, es_principal: false });
      load();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const handleRemove = async (categoriaId: number) => {
    if (!confirm("¿Quitar esta categoría?")) return;
    await productosApi.removeCategoria(productoId, categoriaId);
    load();
  };

  const availableCats = allCats.filter(
    (ac) => !cats.some((c) => c.categoria_id === ac.id)
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-lg max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Categorías de "{productoNombre}"</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">✕</button>
        </div>
        {loading ? <p>Cargando...</p> : (
          <>
            {cats.length === 0 ? (
              <p className="text-gray-500 mb-4">Sin categorías asignadas.</p>
            ) : (
              <table className="w-full border-collapse border mb-4">
                <thead><tr className="bg-gray-200">
                  <th className="border p-2 text-left">Categoría</th>
                  <th className="border p-2 text-left">Principal</th>
                  <th className="border p-2 text-left">Acciones</th>
                </tr></thead>
                <tbody>
                  {cats.map((c) => (
                    <tr key={c.categoria_id}>
                      <td className="border p-2">{c.categoria_nombre}</td>
                      <td className="border p-2">{c.es_principal ? "Sí" : "No"}</td>
                      <td className="border p-2">
                        <button onClick={() => handleRemove(c.categoria_id)}
                          className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Quitar</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {!showAdd ? (
              <button onClick={() => setShowAdd(true)}
                className="bg-green-600 text-white px-4 py-1 rounded cursor-pointer">+ Agregar Categoría</button>
            ) : (
              <div className="border p-3 rounded bg-gray-50">
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <div>
                    <label className="block text-sm font-medium">Categoría</label>
                    <select value={addForm.categoria_id}
                      onChange={(e) => setAddForm({ ...addForm, categoria_id: Number(e.target.value) })}
                      className="border px-2 py-1 rounded w-full">
                      <option value={0}>-- Seleccionar --</option>
                      {availableCats.map((ac) => (
                        <option key={ac.id} value={ac.id}>{ac.nombre}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm">Principal</label>
                    <input type="checkbox" checked={addForm.es_principal}
                      onChange={(e) => setAddForm({ ...addForm, es_principal: e.target.checked })} />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button onClick={handleAdd}
                    className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Confirmar</button>
                  <button onClick={() => setShowAdd(false)}
                    className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer">Cancelar</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* ── Modal de selección de medida (para productos con medidas) ── */
function MedidaSelectorModal({
  producto,
  onConfirm,
  onClose,
}: {
  producto: Producto;
  onConfirm: (medidaId: number, medidaNombre: string, precio: number, cantidad: number) => void;
  onClose: () => void;
}) {
  const [cantidades, setCantidades] = useState<Record<number, number>>({});
  const [toast, setToast] = useState<string | null>(null);

  const medidas = producto.medidas ?? [];

  const getCantidad = (medidaId: number) => cantidades[medidaId] ?? 1;

  const handleAgregar = (m: ProductoMedida) => {
    const cant = getCantidad(m.id);
    onConfirm(m.id, m.nombre, Number(m.precio), cant);
    setToast(`${cant}x ${m.nombre} de ${producto.nombre} ha sido agregado al carrito!`);
    setTimeout(() => setToast(null), 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Agregar "{producto.nombre}"</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">✕</button>
        </div>

        {toast && (
          <div className="mb-3 p-3 bg-green-100 border border-green-300 text-green-800 rounded text-sm text-center font-medium">
            {toast}
          </div>
        )}

        {medidas.length === 0 ? (
          <p className="text-gray-500">Este producto no tiene medidas disponibles.</p>
        ) : (
          <div className="space-y-3">
            {medidas.map((m) => {
              const sinStock = m.stock === 0 || !m.disponible;
              const cant = getCantidad(m.id);
              return (
                <div
                  key={m.id}
                  className={`border rounded p-3 ${sinStock ? 'bg-gray-100 opacity-60' : 'bg-white'}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <span className="font-medium">{m.nombre}</span>
                      <span className="text-gray-500 ml-2">— ${Number(m.precio).toFixed(2)}</span>
                    </div>
                    {sinStock ? (
                      <span className="text-xs text-red-500 font-medium">{!m.disponible ? 'No disponible' : 'Sin stock'}</span>
                    ) : (
                      <span className="text-xs text-gray-400">Stock: {m.stock}</span>
                    )}
                  </div>
                  {!sinStock && (
                    <div className="flex items-center justify-between">
                      <div className="inline-flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => setCantidades((prev) => ({ ...prev, [m.id]: Math.max(1, (prev[m.id] ?? 1) - 1) }))}
                          disabled={cant <= 1}
                          className="border border-gray-400 bg-white text-gray-700 hover:bg-gray-100 text-sm w-7 h-7 flex items-center justify-center rounded cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          −
                        </button>
                        <span className="w-8 text-center font-mono font-semibold">{cant}</span>
                        <button
                          type="button"
                          onClick={() => setCantidades((prev) => ({ ...prev, [m.id]: (prev[m.id] ?? 1) + 1 }))}
                          disabled={cant >= m.stock}
                          className="border border-gray-400 bg-white text-gray-700 hover:bg-gray-100 text-sm w-7 h-7 flex items-center justify-center rounded cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          +
                        </button>
                      </div>
                      {cant >= m.stock && (
                        <span className="text-xs text-amber-600 font-medium">Stock máximo</span>
                      )}
                      <button
                        type="button"
                        onClick={() => handleAgregar(m)}
                        className="bg-blue-600 text-white px-3 py-1 text-sm rounded cursor-pointer hover:bg-blue-700"
                      >
                        Agregar — ${(Number(m.precio) * cant).toFixed(2)}
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
            <div className="flex justify-center pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-100 cursor-pointer"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Página principal ── */
export default function ProductosCRUD({ role = 'admin' }: { role?: 'admin' | 'stock' | 'pedidos' | 'client' }) {
  const navigate = useNavigate();
  const readOnly = role === 'client';
  const isStockMode = role === 'stock';
  const isAuth = !!getAccessToken();
  const hideCreate = role !== 'admin';
  const hideDelete = role === 'client' || role === 'stock';
  const hideRelations = role === 'client' || role === 'stock';
  const hideExport = role === 'client' || role === 'stock';
  const [state, dispatch] = useReducer(reducer, init);
  const [ingPopup, setIngPopup] = useState<{ id: number; nombre: string } | null>(null);
  const [catPopup, setCatPopup] = useState<{ id: number; nombre: string } | null>(null);
  const [allCats, setAllCats] = useState<Categoria[]>([]);
  const [allIngs, setAllIngs] = useState<Ingrediente[]>([]);
  const [recentlyAdded, setRecentlyAdded] = useState<Set<number>>(new Set());
  const addTimerRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  // Medidas state for create form
  const [newMedida, setNewMedida] = useState({ nombre: '', precio: 0, stock: 0 });
  // Existing medidas for edit/stock-edit
  const [existingMedidas, setExistingMedidas] = useState<ProductoMedida[]>([]);
  const [medidaModalProducto, setMedidaModalProducto] = useState<Producto | null>(null);

  const handleAddToCart = (prod: Producto) => {
    // Si el producto tiene medidas, mostrar modal de selección
    if (prod.medidas && prod.medidas.length > 0) {
      setMedidaModalProducto(prod);
      return;
    }

    // Sin medidas → agregar directo
    addToCart(prod.id, prod.nombre, Number(prod.precio_base));
    triggerFeedback(prod.id);
  };

  const handleMedidaConfirm = (medidaId: number, medidaNombre: string, precio: number, cantidad: number) => {
    const prod = medidaModalProducto;
    if (!prod) return;
    addToCart(prod.id, prod.nombre, precio, cantidad, medidaId, medidaNombre);
    triggerFeedback(prod.id);
  };

  const triggerFeedback = (productoId: number) => {
    setRecentlyAdded((prev) => new Set(prev).add(productoId));
    const existingTimer = addTimerRef.current.get(productoId);
    if (existingTimer) clearTimeout(existingTimer);
    const timer = setTimeout(() => {
      setRecentlyAdded((prev) => {
        const next = new Set(prev);
        next.delete(productoId);
        return next;
      });
      addTimerRef.current.delete(productoId);
    }, 1200);
    addTimerRef.current.set(productoId, timer);
  };

  // Load all categories and ingredients (only for admin/pedidos)
  useEffect(() => {
    if (hideRelations) return;
    categoriasApi.getAll(0, 1000).then(setAllCats).catch(() => {});
    ingredientesApi.getAll(0, 1000).then(setAllIngs).catch(() => {});
  }, [hideRelations]);

  // Load existing medidas for edit/stock-edit
  useEffect(() => {
    if (state.editingId && state.showForm) {
      const found = state.items.find(p => p.id === state.editingId);
      if (found?.medidas && found.medidas.length > 0) {
        setExistingMedidas(found.medidas);
      } else {
        productosApi.getMedidas(state.editingId).then(setExistingMedidas).catch(() => {});
      }
    } else {
      setExistingMedidas([]);
    }
  }, [state.editingId, state.showForm]);

  // Load selected for editing
  useEffect(() => {
    if (state.editingId) {
      Promise.all([
        productosApi.getCategorias(state.editingId),
        productosApi.getIngredientes(state.editingId),
      ]).then(([cats, ings]) => {
        dispatch({ type: "SET_SELECTED_CATEGORIAS", payload: cats.map(c => ({ id: c.categoria_id, nombre: c.categoria_nombre, descripcion: null })) });
        const selectedIngs = ings.map(i => {
          const ing = allIngs.find(ai => ai.id === i.ingrediente_id);
          return { id: i.ingrediente_id, nombre: i.ingrediente_nombre, es_alergeno: ing ? ing.es_alergeno : false };
        });
        dispatch({ type: "SET_SELECTED_INGREDIENTES", payload: selectedIngs });
      });
    }
  }, [state.editingId, allIngs]);

  const fetchData = useCallback(async () => {
    dispatch({ type: "SET_LOADING", payload: true });
    try {
      const data = await productosApi.getAll(state.page * PAGE_SIZE, PAGE_SIZE);
      dispatch({ type: "SET_ITEMS", payload: data });

      // Auto-corregir productos con stock=0 pero disponible=true
      // Solo si el usuario tiene permisos de escritura (no client)
      if (!readOnly) {
        const toFix = data.filter((p) => p.stock_cantidad === 0 && p.disponible === true);
        for (const prod of toFix) {
          try {
            await productosApi.update(prod.id, { disponible: false });
          } catch {
            // Si no tiene permisos, silenciosamente ignoramos
          }
        }
        if (toFix.length > 0) {
          // Recargar para reflejar los cambios
          const freshData = await productosApi.getAll(state.page * PAGE_SIZE, PAGE_SIZE);
          dispatch({ type: "SET_ITEMS", payload: freshData });
        }
      }
    } catch (e) {
      dispatch({ type: "SET_ERROR", payload: (e as Error).message });
    }
  }, [state.page, readOnly]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (state.editingId) {
        if (state.stockEditOnly) {
          if (existingMedidas.length > 0) {
            // Update stock for each medida
            for (const m of existingMedidas) {
              await productosApi.updateMedida(state.editingId, m.id, {
                nombre: m.nombre,
                precio: m.precio,
                stock: m.stock,
                disponible: m.disponible,
              });
            }
          } else {
            await productosApi.update(state.editingId, {
              stock_cantidad: state.form.stock_cantidad,
              disponible: state.form.disponible,
            });
          }
        } else {
          await productosApi.update(state.editingId, {
            nombre: state.form.nombre,
            descripcion: state.form.descripcion,
            precio_base: state.form.precio_base,
            stock_cantidad: state.form.stock_cantidad,
            disponible: state.form.disponible,
          });
        }
      } else {
        await productosApi.create(state.form);
      }
      dispatch({ type: "CLOSE_FORM" });
      fetchData();
    } catch (err) {
      let msg = (err as Error).message;
      if (err instanceof AxiosError && err.response?.data) {
        const body = err.response.data as Record<string, unknown>;
        if (body.detail) {
          msg = JSON.stringify(body.detail, null, 2);
        }
      }
      dispatch({ type: "SET_ERROR", payload: msg });
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("¿Eliminar este producto?")) return;
    try {
      await productosApi.delete(id);
      fetchData();
    } catch (err) {
      dispatch({ type: "SET_ERROR", payload: (err as Error).message });
    }
  };

  const filtered = state.items.filter((p) =>
    p.nombre.toLowerCase().includes(state.filter.toLowerCase())
  );

  // Walk up the category tree: any selected category that is primordial,
  // or whose parent/grandparent is primordial, enables medidas
  const catAncestryMap = new Map(allCats.map(c => [c.id, c]));
  const hasPrimordialCategory = state.selectedCategorias.some(sc => {
    let current = catAncestryMap.get(sc.id);
    while (current) {
      if (current.es_primordial) return true;
      current = current.parent_id ? catAncestryMap.get(current.parent_id) : undefined;
    }
    return false;
  });
  const tieneMedidas = (state.form.medidas?.length ?? 0) > 0;

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Gestión de Productos</h1>
      {state.error && <p className="text-red-500 mb-4">{state.error}</p>}

      <div className="flex gap-2 mb-4 items-center">
        {!hideCreate && (
          <button onClick={() => dispatch({ type: "START_CREATE" })}
            className="bg-green-600 text-white px-4 py-1 rounded cursor-pointer">Crear Producto</button>
        )}
        <input type="text" placeholder="Filtrar por nombre..." value={state.filter}
          onChange={(e) => dispatch({ type: "SET_FILTER", payload: e.target.value })}
          className="border px-2 py-1 rounded flex-grow" />
        {!hideExport && (
          <button onClick={() => exportToExcel(filtered.map(({ id, nombre, precio_base, stock_cantidad, disponible, tiempo_prep_min }) => ({
              id, nombre, precio_base, stock_cantidad, tiempo_prep_min, disponible: disponible ? "Sí" : "No",
            })), "productos")}
            className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Exportar Excel</button>
        )}
      </div>

      {state.showForm && (!hideCreate || state.stockEditOnly) && (
        <form onSubmit={handleSubmit} className="border p-4 mb-4 rounded bg-gray-50">
          {state.stockEditOnly ? (
            existingMedidas.length > 0 ? (
              /* ── STOCK: editor de stock por medida ── */
              <div className="mb-4">
                <h3 className="text-lg font-medium mb-2">Stock por Medida</h3>
                {existingMedidas.map(m => (
                  <div key={m.id} className="flex gap-2 items-center mb-2">
                    <span className="w-1/4 font-medium">{m.nombre}</span>
                    <input type="number" min="0" value={m.stock}
                      onChange={(e) => setExistingMedidas(prev =>
                        prev.map(pm => pm.id === m.id ? { ...pm, stock: Number(e.target.value) } : pm)
                      )}
                      className="border px-2 py-1 rounded w-20" />
                    <label className="text-sm flex items-center gap-1 ml-2">
                      <input type="checkbox" checked={m.disponible}
                        onChange={(e) => setExistingMedidas(prev =>
                          prev.map(pm => pm.id === m.id ? { ...pm, disponible: e.target.checked } : pm)
                        )}
                        className="cursor-pointer" />
                      Disponible
                    </label>
                  </div>
                ))}
              </div>
            ) : (
              /* ── STOCK: legacy stock_cantidad ── */
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium">Stock</label>
                  <input type="number" min="0" value={state.form.stock_cantidad ?? 0}
                    onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { stock_cantidad: Number(e.target.value) } })}
                    className="border px-2 py-1 rounded w-full" />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-sm font-medium">Disponible</label>
                  <input type="checkbox" checked={state.form.disponible ?? true}
                    onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { disponible: e.target.checked } })} />
                </div>
              </div>
            )
          ) : (
            /* ── ADMIN/PEDIDOS: formulario completo ── */
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium">Nombre</label>
                <input value={state.form.nombre}
                  onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { nombre: e.target.value } })}
                  className="border px-2 py-1 rounded w-full" required />
              </div>
              <div>
                <label className="block text-sm font-medium">Descripción</label>
                <input value={state.form.descripcion ?? ""}
                  onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { descripcion: e.target.value } })}
                  className="border px-2 py-1 rounded w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium">Precio Base</label>
                <input type="number" step="0.01" value={state.form.precio_base ?? 0}
                  onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { precio_base: Number(e.target.value) } })}
                  className="border px-2 py-1 rounded w-full" />
              </div>
              <div>
                <label className="block text-sm font-medium">Stock</label>
                {(() => {
                  const stockDisabled = (!state.editingId && hasPrimordialCategory) || (!!state.editingId && existingMedidas.length > 0);
                  return (
                    <>
                      <input type="number" min="0" value={state.form.stock_cantidad ?? 0}
                        disabled={stockDisabled}
                        onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { stock_cantidad: Number(e.target.value) } })}
                        className={`border px-2 py-1 rounded w-full ${stockDisabled ? 'bg-gray-200 text-gray-400 cursor-not-allowed' : ''}`} />
                      {stockDisabled && (
                        <p className="text-xs text-gray-500 mt-1 italic">El stock se gestiona a través de las medidas/porciones.</p>
                      )}
                    </>
                  );
                })()}
              </div>
              <div>
                <label className="block text-sm font-medium">Tiempo Prep. (min)</label>
                <input type="number" value={state.form.tiempo_prep_min ?? 0}
                  onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { tiempo_prep_min: Number(e.target.value) } })}
                  className="border px-2 py-1 rounded w-full" />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm font-medium">Disponible</label>
                <input type="checkbox" checked={state.form.disponible ?? true}
                  onChange={(e) => dispatch({ type: "UPDATE_FORM", payload: { disponible: e.target.checked } })} />
              </div>
            </div>
          )}

          {/* ── Selectores de Categorías e Ingredientes (inline, antes de los botones) ── */}
          {!state.editingId && !hideCreate && !isStockMode && (
            <>
              <div className="border p-4 mb-4 rounded bg-gray-50">
                <h3 className="text-lg font-medium mb-2">Categorías</h3>
                {state.selectedCategorias.length > 0 && (
                  <table className="w-full border-collapse border mb-2">
                    <thead><tr className="bg-gray-200">
                      <th className="border p-2 text-left">Nombre</th>
                      <th className="border p-2 text-left">Descripción</th>
                      <th className="border p-2 text-left">Acción</th>
                    </tr></thead>
                    <tbody>
                      {state.selectedCategorias.map((c) => (
                        <tr key={c.id}>
                          <td className="border p-2">{c.nombre}</td>
                          <td className="border p-2">{c.descripcion ?? "-"}</td>
                          <td className="border p-2">
                            <button type="button" onClick={() => dispatch({ type: "SET_SELECTED_CATEGORIAS", payload: state.selectedCategorias.filter(sc => sc.id !== c.id) })} className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Quitar</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <button type="button" onClick={() => dispatch({ type: "SET_SHOW_CATEGORIA_SELECTOR", payload: true })} className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Seleccionar Categorías</button>
              </div>

              <div className={`border p-4 mb-4 rounded ${tieneMedidas && hasPrimordialCategory ? 'bg-gray-100 opacity-60' : 'bg-gray-50'}`}>
                <h3 className="text-lg font-medium mb-2 flex items-center gap-2">
                  Ingredientes
                  {tieneMedidas && hasPrimordialCategory && (
                    <span className="text-xs text-gray-500 font-normal italic">(no aplica — el producto usa medidas/porciones)</span>
                  )}
                </h3>
                {state.selectedIngredientes.length > 0 && (
                  <table className="w-full border-collapse border mb-2">
                    <thead><tr className="bg-gray-200">
                      <th className="border p-2 text-left">Nombre</th>
                      <th className="border p-2 text-left">Alérgeno</th>
                      <th className="border p-2 text-left">Acción</th>
                    </tr></thead>
                    <tbody>
                      {state.selectedIngredientes.map((i) => (
                        <tr key={i.id}>
                          <td className="border p-2">{i.nombre}</td>
                          <td className="border p-2">{i.es_alergeno ? "Sí" : "No"}</td>
                          <td className="border p-2">
                            <button type="button" onClick={() => dispatch({ type: "SET_SELECTED_INGREDIENTES", payload: state.selectedIngredientes.filter(si => si.id !== i.id) })} className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Quitar</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <button type="button" disabled={tieneMedidas && hasPrimordialCategory}
                  onClick={() => dispatch({ type: "SET_SHOW_INGREDIENTE_SELECTOR", payload: true })}
                  className={`px-4 py-1 rounded cursor-pointer ${tieneMedidas && hasPrimordialCategory ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-blue-600 text-white'}`}>Seleccionar Ingredientes</button>
              </div>
            </>
          )}

          {/* ── Medidas / Porciones (solo creación con categoría primordial) ── */}
          {!state.stockEditOnly && !state.editingId && hasPrimordialCategory && (
            <div className="border p-4 mb-4 rounded bg-gray-50">
              <h3 className="text-lg font-medium mb-2">Medidas / Porciones</h3>

              {(!state.form.medidas || state.form.medidas.length === 0) ? (
                <p className="text-gray-500 mb-4">Sin medidas definidas.</p>
              ) : (
                <table className="w-full border-collapse border mb-4">
                  <thead><tr className="bg-gray-200">
                    <th className="border p-2 text-left">Nombre</th>
                    <th className="border p-2 text-left">Precio</th>
                    <th className="border p-2 text-left">Stock</th>
                    <th className="border p-2 text-left">Acción</th>
                  </tr></thead>
                  <tbody>
                    {state.form.medidas.map((m, idx) => (
                      <tr key={idx}>
                        <td className="border p-2">{m.nombre}</td>
                        <td className="border p-2">${m.precio}</td>
                        <td className="border p-2">{m.stock ?? 0}</td>
                        <td className="border p-2">
                          <button type="button" onClick={() => {
                            const current = state.form.medidas ?? [];
                            dispatch({ type: "UPDATE_FORM", payload: { medidas: current.filter((_, i) => i !== idx) } });
                          }} className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Quitar</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}

              {/* Add medida inline form */}
              <div className="border p-3 rounded bg-white">
                <div className="grid grid-cols-3 gap-2 mb-2">
                  <div>
                    <label className="block text-sm font-medium">Nombre</label>
                    <input type="text" value={newMedida.nombre}
                      onChange={(e) => setNewMedida({ ...newMedida, nombre: e.target.value })}
                      className="border px-2 py-1 rounded w-full" placeholder="Ej: 1/2 kg" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium">Precio</label>
                    <input type="number" step="0.01" min="0" value={newMedida.precio}
                      onChange={(e) => setNewMedida({ ...newMedida, precio: Number(e.target.value) })}
                      className="border px-2 py-1 rounded w-full" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium">Stock</label>
                    <input type="number" min="0" value={newMedida.stock}
                      onChange={(e) => setNewMedida({ ...newMedida, stock: Number(e.target.value) })}
                      className="border px-2 py-1 rounded w-full" />
                  </div>
                </div>
                <button type="button" onClick={() => {
                  if (!newMedida.nombre.trim()) return;
                  dispatch({
                    type: "UPDATE_FORM",
                    payload: { medidas: [...(state.form.medidas ?? []), { ...newMedida }] },
                  });
                  setNewMedida({ nombre: '', precio: 0, stock: 0 });
                }} className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Agregar</button>
              </div>
            </div>
          )}

          <div className="flex gap-2 mt-4">
            <button type="submit" className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">
              {state.stockEditOnly ? "Actualizar Stock" : (state.editingId ? "Actualizar" : "Crear")}</button>
            <button type="button" onClick={() => dispatch({ type: "CLOSE_FORM" })}
              className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer">Cancelar</button>
          </div>
        </form>
      )}

      {state.loading ? <p>Cargando...</p> : (
        <table className="w-full border-collapse border">
          <thead><tr className="bg-gray-200">
            {!readOnly && <th className="border p-2 text-left">ID</th>}
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Precio</th>
            {!readOnly && <th className="border p-2 text-left">Stock</th>}
            {!isStockMode && <th className="border p-2 text-left">Prep (min)</th>}
            <th className="border p-2 text-left">Disponible</th>
            {!readOnly && !isStockMode && (
              <th className="border p-2 text-left">Relaciones</th>
            )}
            {!readOnly && (
              <th className="border p-2 text-left">Acciones</th>
            )}
            {isAuth && <th className="border p-2 text-left">Agregar al carrito</th>}
          </tr></thead>
          <tbody>
            {filtered.map((prod) => (
              <tr key={prod.id} className="hover:bg-gray-100">
                {!readOnly && <td className="border p-2">{prod.id}</td>}
                <td className="border p-2">{prod.nombre}</td>
                <td className="border p-2">${prod.precio_base}</td>
                {!readOnly && (
                  <td className="border p-2">
                    {(() => {
                      const totalStock = prod.medidas?.length
                        ? prod.medidas.reduce((s, m) => s + m.stock, 0)
                        : prod.stock_cantidad;
                      return (
                        <span className={`font-mono font-semibold ${totalStock === 0 ? 'text-red-600' : 'text-green-700'}`}>
                          {totalStock}
                        </span>
                      );
                    })()}
                  </td>
                )}
                {!isStockMode && <td className="border p-2">{prod.tiempo_prep_min}</td>}
                <td className="border p-2">
                  {(() => {
                    // Para productos con medidas, mostrar disponibilidad individual
                    if (prod.medidas && prod.medidas.length > 0) {
                      const disponibles = prod.medidas.filter(m => m.disponible && m.stock > 0).length;
                      const total = prod.medidas.length;
                      if (disponibles === total) {
                        return <span className="font-medium text-green-700">Sí</span>;
                      }
                      if (disponibles === 0) {
                        return <span className="font-medium text-red-600">No</span>;
                      }
                      return <span className="font-medium text-amber-600">Algunos sí</span>;
                    }
                    return (
                      <span className={`font-medium ${prod.disponible ? 'text-green-700' : 'text-red-600'}`}>
                        {prod.disponible ? "Sí" : "No"}
                      </span>
                    );
                  })()}
                </td>
                {!readOnly && !isStockMode && (
                  <td className="border p-2">
                    <div className="flex gap-1">
                      <button onClick={() => setIngPopup({ id: prod.id, nombre: prod.nombre })}
                        className="bg-purple-600 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-purple-700">Ingredientes</button>
                      <button onClick={() => setCatPopup({ id: prod.id, nombre: prod.nombre })}
                        className="bg-teal-600 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-teal-700">Categorías</button>
                    </div>
                  </td>
                )}
                {!readOnly && (
                  <td className="border p-2">
                    <div className="flex gap-1 flex-wrap">
                      {!isStockMode && (
                        <button onClick={() => dispatch({ type: "START_EDIT", payload: prod })}
                          className="bg-yellow-500 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-yellow-600">Editar</button>
                      )}
                      <button onClick={() => dispatch({ type: "START_STOCK_EDIT", payload: prod })}
                        className="bg-amber-700 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-amber-800">Gestionar Stock</button>
                      {!isStockMode && !hideDelete && (
                        <button onClick={() => handleDelete(prod.id)}
                          className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-red-700">Eliminar</button>
                      )}
                    </div>
                  </td>
                )}
                {isAuth && (
                  <td className="border p-2">
                    <button
                      onClick={() => handleAddToCart(prod)}
                      className={`px-2 py-1 rounded text-sm cursor-pointer transition-colors ${
                        recentlyAdded.has(prod.id)
                          ? "bg-green-600 text-white"
                          : "bg-blue-600 text-white hover:bg-blue-700"
                      }`}
                    >
                      {recentlyAdded.has(prod.id) ? "✓ Agregado" : "Agregar al carrito"}
                    </button>
                  </td>
                )}
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={readOnly ? 5 : (isStockMode ? 7 : isAuth ? 9 : 8)} className="border p-2 text-center text-gray-500">Sin resultados</td></tr>}
          </tbody>
        </table>
      )}

      <div className="flex gap-2 mt-4 items-center justify-between">
        <div className="flex gap-2 items-center">
          <button disabled={state.page === 0}
            onClick={() => dispatch({ type: "SET_PAGE", payload: state.page - 1 })}
            className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer">← Anterior</button>
          <span>Página {state.page + 1}</span>
          <button disabled={state.items.length < PAGE_SIZE}
            onClick={() => dispatch({ type: "SET_PAGE", payload: state.page + 1 })}
            className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer">Siguiente →</button>
        </div>
        {isAuth && (
          <button
            onClick={() => navigate("/carrito")}
            className="bg-green-700 text-white px-4 py-1.5 rounded text-sm font-semibold hover:bg-green-800 cursor-pointer"
          >
            Ver Carrito {getItemCount() > 0 ? `(${getItemCount()})` : ""}
          </button>
        )}
      </div>

      {/* Popups */}
      {ingPopup && <IngredientesPopup productoId={ingPopup.id} productoNombre={ingPopup.nombre} onClose={() => setIngPopup(null)} />}
      {catPopup && <CategoriasPopup productoId={catPopup.id} productoNombre={catPopup.nombre} onClose={() => setCatPopup(null)} />}

      {/* Selectores para creación */}
      {state.showCategoriaSelector && (
        <CategoriaSelector
          allCategorias={allCats}
          selectedIds={state.selectedCategorias.map(c => c.id)}
          onSelect={(ids) => {
            const selectedCats = allCats.filter(c => ids.includes(c.id)).map(c => ({ id: c.id, nombre: c.nombre, descripcion: c.descripcion }));
            dispatch({ type: "SET_SELECTED_CATEGORIAS", payload: selectedCats });
          }}
          onClose={() => dispatch({ type: "SET_SHOW_CATEGORIA_SELECTOR", payload: false })}
        />
      )}

      {state.showIngredienteSelector && (
        <IngredienteSelector
          allIngredientes={allIngs}
          selectedIds={state.selectedIngredientes.map(i => i.id)}
          onSelect={(ids) => {
            const selectedIngs = allIngs.filter(i => ids.includes(i.id)).map(i => ({ id: i.id, nombre: i.nombre, es_alergeno: i.es_alergeno }));
            dispatch({ type: "SET_SELECTED_INGREDIENTES", payload: selectedIngs });
          }}
          onClose={() => dispatch({ type: "SET_SHOW_INGREDIENTE_SELECTOR", payload: false })}
        />
      )}

      {/* Modal de selección de medida */}
      {medidaModalProducto && (
        <MedidaSelectorModal
          producto={medidaModalProducto}
          onConfirm={handleMedidaConfirm}
          onClose={() => setMedidaModalProducto(null)}
        />
      )}
    </div>
  );
}
