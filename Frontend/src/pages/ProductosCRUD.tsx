/**
 * ProductosCRUD — Product management page with role-based views.
 *
 * Roles and what they see:
 *   - admin:   full CRUD + category/ingredient management + variant bulk creation.
 *   - stock:   stock-only editing (quantity, availability toggle).
 *   - pedidos: full view but no create/delete (mid-level access).
 *   - client:  read-only menu view with "Agregar al carrito" button.
 *
 * Features:
 *   - Paginated product list with client-side text filter.
 *   - Inline form for create/edit (full or stock-only mode).
 *   - Category and ingredient association via popup selectors.
 *   - Bulk variant creation modal (base name + multiple size/price variants).
 *   - Ingredient popup with quantity management and allergen toggles.
 *   - Category popup for viewing/adding/removing product-category links.
 *   - "Add to cart" integration with visual feedback animation.
 *   - Excel export of filtered data.
 *   - Auto-correction: products with stock=0 but disponible=true are set to false.
 *
 * State management: useReducer for the data grid, TanStack Form for create/edit.
 */

import { useReducer, useEffect, useCallback, useState, useRef } from "react";
import { useAppForm } from "../hooks/useAppForm";
import type { Producto, ProductoCreate, ProductoIngredienteRead, ProductoCategoriaRead } from "../api/productos";
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

/** All state for the data grid and modal/sub-form visibility. */
interface State {
  items: Producto[];
  loading: boolean;
  error: string | null;
  page: number;
  filter: string;
  editingId: number | null;
  showForm: boolean;
  stockEditOnly: boolean;
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
  | { type: "SET_SELECTED_CATEGORIAS"; payload: {id: number, nombre: string, descripcion: string | null}[] }
  | { type: "SET_SELECTED_INGREDIENTES"; payload: {id: number, nombre: string, es_alergeno: boolean}[] }
  | { type: "SET_SHOW_CATEGORIA_SELECTOR"; payload: boolean }
  | { type: "SET_SHOW_INGREDIENTE_SELECTOR"; payload: boolean };

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
        selectedCategorias: [],
        selectedIngredientes: [],
        showCategoriaSelector: false,
        showIngredienteSelector: false,
      };
    case "START_STOCK_EDIT":
      return {
        ...state, editingId: action.payload.id, showForm: true, stockEditOnly: true,
        selectedCategorias: [],
        selectedIngredientes: [],
        showCategoriaSelector: false,
        showIngredienteSelector: false,
      };
    case "START_CREATE": return { ...state, editingId: null, showForm: true, stockEditOnly: false, selectedCategorias: [], selectedIngredientes: [], showCategoriaSelector: false, showIngredienteSelector: false };
    case "CLOSE_FORM": return { ...state, showForm: false, editingId: null, stockEditOnly: false, selectedCategorias: [], selectedIngredientes: [], showCategoriaSelector: false, showIngredienteSelector: false };
    case "SET_SELECTED_CATEGORIAS": return { ...state, selectedCategorias: action.payload };
    case "SET_SELECTED_INGREDIENTES": return { ...state, selectedIngredientes: action.payload };
    case "SET_SHOW_CATEGORIA_SELECTOR": return { ...state, showCategoriaSelector: action.payload };
    case "SET_SHOW_INGREDIENTE_SELECTOR": return { ...state, showIngredienteSelector: action.payload };
    default: return state;
  }
}

const init: State = {
  items: [], loading: false, error: null, page: 0, filter: "",
  editingId: null, showForm: false, stockEditOnly: false,
  selectedCategorias: [], selectedIngredientes: [], showCategoriaSelector: false, showIngredienteSelector: false,
};

/* ── Selector de Categorias (para creacion) ── */

/**
 * Modal for selecting categories to assign to a new product.
 * Uses a simple checkbox table. Supports multi-select.
 */
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
          <h2 className="text-lg font-bold">Seleccionar Categorias</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">X</button>
        </div>
        <table className="w-full border-collapse border mb-4">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Seleccionar</th>
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Descripcion</th>
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

/* ── Selector de Ingredientes (para creacion) ── */

/**
 * Modal for selecting ingredients to assign to a new product.
 * Shows allergen info, price, and stock for each ingredient.
 */
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
          <h2 className="text-lg font-bold">Seleccionar Insumos</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">X</button>
        </div>
        <table className="w-full border-collapse border mb-4">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Seleccionar</th>
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Alergeno</th>
            <th className="border p-2 text-left">Precio</th>
            <th className="border p-2 text-left">Stock</th>
          </tr></thead>
          <tbody>
            {allIngredientes.map((ing) => (
              <tr key={ing.id}>
                <td className="border p-2">
                  <input type="checkbox" checked={localSelected.includes(ing.id)} onChange={() => toggleIngredient(ing.id)} />
                </td>
                <td className="border p-2">{ing.nombre}</td>
                <td className="border p-2">{ing.es_alergeno ? "Si" : "No"}</td>
                <td className="border p-2">${Number(ing.precio_actual).toFixed(2)}</td>
                <td className="border p-2">{ing.stock_actual}</td>
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

/**
 * Modal for managing a product's ingredient relationships.
 *
 * Features:
 *   - View all assigned ingredients with order, quantity, cost, and flags.
 *   - Update quantity inline (optimistic update with revert on error).
 *   - Remove an ingredient from the product.
 *   - Add a new ingredient (with cantidad, orden, removible, principal flags).
 *   - Toggle es_alergeno on ingredients directly (admin convenience).
 *   - Shows calculated total ingredient cost for the product.
 */
function IngredientesPopup({ productoId, productoNombre, onClose }: {
  productoId: number; productoNombre: string; onClose: () => void;
}) {
  const [ings, setIngs] = useState<ProductoIngredienteRead[]>([]);
  const [allIngs, setAllIngs] = useState<Ingrediente[]>([]);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState<number | null>(null);
  const [addForm, setAddForm] = useState({ ingrediente_id: 0, cantidad: 1, es_removible: true, es_principal: false, orden: 0 });
  const [showAdd, setShowAdd] = useState(false);
  const [updatingCantidad, setUpdatingCantidad] = useState<number | null>(null);

  /** Loads both the product's current ingredients and all available ingredients. */
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

  /**
   * Silent refresh — fetches updated data WITHOUT setting loading=true.
   * Used by handleToggleAlergeno and handleCantidadChange to avoid
   * flashing "Cargando..." during background updates.
   */
  const refresh = useCallback(async () => {
    const [prodIngs, available] = await Promise.all([
      productosApi.getIngredientes(productoId),
      ingredientesApi.getAll(0, 1000),
    ]);
    setIngs(prodIngs);
    setAllIngs(available);
  }, [productoId]);

  useEffect(() => { load(); }, [load]);

  /** Adds a new ingredient relationship to the product. */
  const handleAdd = async () => {
    if (!addForm.ingrediente_id) return;
    await productosApi.addIngrediente(productoId, addForm);
    setShowAdd(false);
    setAddForm({ ingrediente_id: 0, cantidad: 1, es_removible: true, es_principal: false, orden: 0 });
    refresh();
  };

  /**
   * Updates ingredient quantity with optimistic UI update.
   * If the API call fails, the local state is reverted by reloading from the server.
   */
  const handleCantidadChange = async (ingredienteId: number, newCantidad: number) => {
    if (newCantidad < 1) return;
    setUpdatingCantidad(ingredienteId);
    // Optimistic update: immediately update local state
    setIngs(prev => prev.map(ing =>
      ing.ingrediente_id === ingredienteId
        ? { ...ing, cantidad: newCantidad }
        : ing
    ));
    try {
      await productosApi.updateIngredienteCantidad(productoId, ingredienteId, newCantidad);
    } catch {
      // Revert on error: reload from server
      refresh();
    } finally {
      setUpdatingCantidad(null);
    }
  };

  /** Removes an ingredient from the product. */
  const handleRemove = async (ingredienteId: number) => {
    if (!confirm("Quitar este ingrediente?")) return;
    await productosApi.removeIngrediente(productoId, ingredienteId);
    refresh();
  };

  /** Toggles the es_alergeno flag on an ingredient directly from this popup. */
  const handleToggleAlergeno = async (ingredienteId: number, currentValue: boolean) => {
    setToggling(ingredienteId);
    try {
      await ingredientesApi.update(ingredienteId, { es_alergeno: !currentValue });
      await refresh(); // Silently reload to reflect changes
    } catch (err) {
      console.error("[alergeno-toggle] Error al cambiar alergeno:", err);
      alert("Error al cambiar alergeno. Revisa que tengas permisos de administrador o stock.");
    } finally {
      setToggling(null);
    }
  };

  /** Resolves full ingredient info from the master list by ID. */
  const getIngInfo = (ingredienteId: number) =>
    allIngs.find((i) => i.id === ingredienteId);

  /** Ingredients not yet assigned to this product. */
  const availableIngs = allIngs.filter(
    (ai) => !ings.some((i) => i.ingrediente_id === ai.id)
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-2xl max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Insumos de &quot;{productoNombre}&quot;</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">X</button>
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
                  <th className="border p-2 text-left">Cantidad</th>
                  <th className="border p-2 text-left">Costo</th>
                  <th className="border p-2 text-left">Alergeno</th>
                  <th className="border p-2 text-left">Removible</th>
                  <th className="border p-2 text-left">Principal</th>
                  <th className="border p-2 text-left">Acciones</th>
                </tr></thead>
                <tbody>
                  {(() => {
                    /** Sum of (ingredient cost * quantity) across all assigned ingredients. */
                    const totalCalculado = ings.reduce((sum, ing) => {
                      const info = getIngInfo(ing.ingrediente_id);
                      const precio = info?.precio_actual ?? 0;
                      return sum + Number(precio) * Number(ing.cantidad);
                    }, 0);
                    return (
                      <>
                        {ings.map((ing) => {
                          const info = getIngInfo(ing.ingrediente_id);
                          const isAlergeno = info?.es_alergeno ?? false;
                          const precioIng = info?.precio_actual ?? 0;
                          const cost = Number(precioIng) * Number(ing.cantidad);
                          return (
                            <tr key={ing.ingrediente_id}>
                              <td className="border p-2">{ing.orden}</td>
                              <td className="border p-2">{ing.ingrediente_nombre}</td>
                              <td className="border p-2">
                                <input type="number" min="1"
                                  value={ing.cantidad}
                                  disabled={updatingCantidad === ing.ingrediente_id}
                                  onChange={(e) => handleCantidadChange(ing.ingrediente_id, parseInt(e.target.value) || 1)}
                                  className="border px-2 py-1 rounded w-20" />
                              </td>
                              <td className="border p-2 font-mono">
                                ${cost.toFixed(2)}
                              </td>
                              <td className="border p-2">
                                <span className="inline-flex items-center gap-1">
                                  <span className={isAlergeno ? "text-red-600 font-medium" : "text-gray-500"}>
                                    {isAlergeno ? "Si" : "No"}
                                  </span>
                                  <button
                                    onClick={() => handleToggleAlergeno(ing.ingrediente_id, isAlergeno)}
                                    disabled={toggling === ing.ingrediente_id}
                                    className="text-xs border border-gray-400 rounded px-1.5 py-0.5 hover:bg-gray-100 cursor-pointer disabled:opacity-50"
                                    title={isAlergeno ? "Mark as non-allergen" : "Mark as allergen"}
                                  >
                                    {toggling === ing.ingrediente_id ? "..." : "Cambiar"}
                                  </button>
                                </span>
                              </td>
                              <td className="border p-2">{ing.es_removible ? "Si" : "No"}</td>
                              <td className="border p-2">{ing.es_principal ? "Si" : "No"}</td>
                              <td className="border p-2">
                                <button onClick={() => handleRemove(ing.ingrediente_id)}
                                  className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-red-700">Quitar</button>
                              </td>
                            </tr>
                          );
                        })}
                        {ings.length > 0 && (
                          <tr className="bg-gray-100 font-semibold">
                            <td colSpan={2} className="border p-2 text-right">Costo total calculado:</td>
                            <td className="border p-2"></td>
                            <td className="border p-2 font-mono">${totalCalculado.toFixed(2)}</td>
                            <td colSpan={4} className="border p-2"></td>
                          </tr>
                        )}
                      </>
                    );
                  })()}
                </tbody>
              </table>
            )}

            {/* Add ingredient form (toggled by button) */}
            {!showAdd ? (
              <button onClick={() => setShowAdd(true)}
                className="bg-green-600 text-white px-4 py-1 rounded cursor-pointer hover:bg-green-700">+ Agregar Ingrediente</button>
            ) : (
              <div className="border p-3 rounded bg-gray-50">
                <div className="grid grid-cols-3 gap-2 mb-2">
                  <div>
                    <label className="block text-sm font-medium">Ingrediente</label>
                    <select value={addForm.ingrediente_id}
                      onChange={(e) => setAddForm({ ...addForm, ingrediente_id: Number(e.target.value) })}
                      className="border px-2 py-1 rounded w-full">
                      <option value={0}>-- Seleccionar --</option>
                      {availableIngs.map((ai) => (
                        <option key={ai.id} value={ai.id}>{ai.nombre} (${Number(ai.precio_actual).toFixed(2)})</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium">Cantidad</label>
                    <input type="number" min="1" value={addForm.cantidad}
                      onChange={(e) => setAddForm({ ...addForm, cantidad: parseInt(e.target.value) || 1 })}
                      className="border px-2 py-1 rounded w-full" />
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

/* ── Popup de Categorias ── */

/**
 * Modal for managing a product's category assignments.
 * Shows assigned categories and allows adding/removing.
 */
function CategoriasPopup({ productoId, productoNombre, onClose }: {
  productoId: number; productoNombre: string; onClose: () => void;
}) {
  const [cats, setCats] = useState<ProductoCategoriaRead[]>([]);
  const [allCats, setAllCats] = useState<Categoria[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [addForm, setAddForm] = useState({ categoria_id: 0, es_principal: false });

  /** Loads both the product's current categories and all available categories. */
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

  /** Adds a category assignment to the product. */
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

  /** Removes a category assignment from the product. */
  const handleRemove = async (categoriaId: number) => {
    if (!confirm("Quitar esta categoria?")) return;
    await productosApi.removeCategoria(productoId, categoriaId);
    load();
  };

  /** Categories not yet assigned to this product. */
  const availableCats = allCats.filter(
    (ac) => !cats.some((c) => c.categoria_id === ac.id)
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-lg max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Categorias de &quot;{productoNombre}&quot;</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">X</button>
        </div>
        {loading ? <p>Cargando...</p> : (
          <>
            {cats.length === 0 ? (
              <p className="text-gray-500 mb-4">Sin categorias asignadas.</p>
            ) : (
              <table className="w-full border-collapse border mb-4">
                <thead><tr className="bg-gray-200">
                  <th className="border p-2 text-left">Categoria</th>
                  <th className="border p-2 text-left">Principal</th>
                  <th className="border p-2 text-left">Acciones</th>
                </tr></thead>
                <tbody>
                  {cats.map((c) => (
                    <tr key={c.categoria_id}>
                      <td className="border p-2">{c.categoria_nombre}</td>
                      <td className="border p-2">{c.es_principal ? "Si" : "No"}</td>
                      <td className="border p-2">
                        <button onClick={() => handleRemove(c.categoria_id)}
                          className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Quitar</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            {/* Add category form (toggled by button) */}
            {!showAdd ? (
              <button onClick={() => setShowAdd(true)}
                className="bg-green-600 text-white px-4 py-1 rounded cursor-pointer">+ Agregar Categoria</button>
            ) : (
              <div className="border p-3 rounded bg-gray-50">
                <div className="grid grid-cols-2 gap-2 mb-2">
                  <div>
                    <label className="block text-sm font-medium">Categoria</label>
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

/* ── Modal de Creacion por Lotes (Variantes) ── */

/**
 * Modal for bulk-creating product variants from a base name.
 *
 * The user enters a base name (e.g., "Cafe Latte"), then adds rows
 * with size/price/stock (e.g., "Chico", "Grande"). Each row creates
 * a separate product with the name: "{baseName} {variantName}".
 *
 * Categories are shared across all variants.
 * Results are reported: created count + any failures with error messages.
 */
function CrearVariantesModal({ allCategorias, onClose, onComplete }: {
  allCategorias: Categoria[];
  onClose: () => void;
  onComplete: () => void;
}) {
  const [nombreBase, setNombreBase] = useState("");
  const [variants, setVariants] = useState<{nombre: string; precio: string; stock: string}[]>([
    {nombre: "", precio: "", stock: "0"}
  ]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [showCategorySelector, setShowCategorySelector] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<{created: number; failed: {nombre: string; error: string}[]} | null>(null);

  /** Adds a new variant row (max 10). */
  const addRow = () => {
    if (variants.length >= 10) return;
    setVariants([...variants, {nombre: "", precio: "", stock: "0"}]);
  };

  /** Removes a variant row (minimum 1). */
  const removeRow = (idx: number) => {
    if (variants.length <= 1) return;
    setVariants(variants.filter((_, i) => i !== idx));
  };

  /**
   * Submits all variants in parallel via Promise.allSettled.
   * Reports which succeeded and which failed.
   * If all succeed, auto-closes the modal.
   */
  const handleSubmit = async () => {
    if (!nombreBase.trim()) { alert("El nombre base es obligatorio"); return; }
    if (selectedCategoryIds.length === 0) { alert("Seleccione al menos una categoria"); return; }

    const invalidVariant = variants.find(v => !v.nombre.trim() || !v.precio || Number(v.precio) <= 0);
    if (invalidVariant) { alert("Cada variante debe tener nombre y precio mayor a 0"); return; }

    setSubmitting(true);
    const results = await Promise.allSettled(
      variants.map(v =>
        productosApi.create({
          nombre: `${nombreBase.trim()} ${v.nombre.trim()}`,
          precio_base: Number(v.precio),
          stock_cantidad: Number(v.stock) || 0,
          categorias_ids: selectedCategoryIds,
          disponible: true,
        })
      )
    );

    const created = results.filter(r => r.status === "fulfilled").length;
    const failed = results
      .map((r, i) => ({r, i}))
      .filter(({r}) => r.status === "rejected")
      .map(({r, i}) => ({
        nombre: `${nombreBase.trim()} ${variants[i].nombre.trim()}`,
        error: ((r as PromiseRejectedResult).reason as Error)?.message || "Error desconocido"
      }));

    setResult({created, failed});
    setSubmitting(false);

    if (failed.length === 0) {
      onComplete();
      onClose();
    }
  };

  const selectedCategoryNames = allCategorias
    .filter(c => selectedCategoryIds.includes(c.id))
    .map(c => c.nombre)
    .join(", ");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-3xl max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Crear Variantes</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">X</button>
        </div>

        {result ? (
          /* Results view (after submission) */
          <div>
            <p className="mb-2">
              <span className="font-semibold text-green-600">{result.created} creadas</span>
              {result.failed.length > 0 && (
                <span className="font-semibold text-red-600 ml-2">
                  , {result.failed.length} fallaron
                </span>
              )}
            </p>
            {result.failed.length > 0 && (
              <div className="mb-4">
                <h4 className="font-medium text-red-700 mb-1">Errores:</h4>
                <ul className="list-disc pl-5 text-sm text-red-600">
                  {result.failed.map((f, i) => (
                    <li key={i}><strong>{f.nombre}</strong>: {f.error}</li>
                  ))}
                </ul>
              </div>
            )}
            <button onClick={onClose}
              className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Cerrar</button>
          </div>
        ) : (
          <>
            {/* Base name input */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Nombre base</label>
              <input type="text" value={nombreBase}
                onChange={(e) => setNombreBase(e.target.value)}
                placeholder="Ej: Cafe Latte"
                className="border px-2 py-1 rounded w-full" />
            </div>

            {/* Category selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Categorias</label>
              <button type="button" onClick={() => setShowCategorySelector(true)}
                className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer text-sm">
                {selectedCategoryIds.length > 0 ? "Cambiar Categorias" : "Seleccionar Categorias"}
              </button>
              {selectedCategoryIds.length > 0 && (
                <p className="text-sm text-gray-600 mt-1">
                  Seleccionadas: {selectedCategoryNames}
                </p>
              )}
            </div>

            {/* Variant rows table */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <label className="text-sm font-medium">Variantes</label>
                {variants.length < 10 && (
                  <button type="button" onClick={addRow}
                    className="bg-green-600 text-white px-3 py-1 rounded text-sm cursor-pointer">+ Agregar Fila</button>
                )}
              </div>
              <table className="w-full border-collapse border">
                <thead><tr className="bg-gray-200">
                  <th className="border p-2 text-left">Nombre del tamano</th>
                  <th className="border p-2 text-left">Precio</th>
                  <th className="border p-2 text-left">Stock</th>
                  <th className="border p-2 text-left">Accion</th>
                </tr></thead>
                <tbody>
                  {variants.map((v, idx) => (
                    <tr key={idx}>
                      <td className="border p-2">
                        <input type="text" value={v.nombre}
                          onChange={(e) => {
                            const next = [...variants];
                            next[idx] = {...next[idx], nombre: e.target.value};
                            setVariants(next);
                          }}
                          placeholder="Ej: Grande"
                          className="border px-2 py-1 rounded w-full" />
                      </td>
                      <td className="border p-2">
                        <input type="number" step="0.01" value={v.precio}
                          onChange={(e) => {
                            const next = [...variants];
                            next[idx] = {...next[idx], precio: e.target.value};
                            setVariants(next);
                          }}
                          className="border px-2 py-1 rounded w-full" />
                      </td>
                      <td className="border p-2">
                        <input type="number" value={v.stock}
                          onChange={(e) => {
                            const next = [...variants];
                            next[idx] = {...next[idx], stock: e.target.value};
                            setVariants(next);
                          }}
                          className="border px-2 py-1 rounded w-full" />
                      </td>
                      <td className="border p-2">
                        {variants.length > 1 && (
                          <button type="button" onClick={() => removeRow(idx)}
                            className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Quitar</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex gap-2">
              <button type="button" onClick={handleSubmit} disabled={submitting}
                className="bg-indigo-600 text-white px-4 py-1 rounded cursor-pointer disabled:opacity-50">
                {submitting ? "Creando..." : `Crear ${variants.length} Variantes`}
              </button>
              <button type="button" onClick={onClose}
                className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer">Cancelar</button>
            </div>

            {/* Category selector sub-modal */}
            {showCategorySelector && (
              <CategoriaSelector
                allCategorias={allCategorias}
                selectedIds={selectedCategoryIds}
                onSelect={(ids) => setSelectedCategoryIds(ids)}
                onClose={() => setShowCategorySelector(false)}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* ── Pagina principal ── */

/**
 * ProductosCRUD — Main product management component.
 *
 * Role-based behavior is determined by the `role` prop:
 *   - admin:   full access (CRUD, relations, create variants, export).
 *   - stock:   stock-only mode (update stock_cantidad + disponible flag).
 *   - pedidos: full view, can edit but cannot create/delete.
 *   - client:  read-only menu view with "Agregar al carrito" only.
 *
 * Cart integration:
 *   - Only authenticated users (isAuth) see the "Add to cart" column.
 *   - Recently-added items get a visual feedback animation (green flash).
 *   - Products without stock or not available are disabled.
 */
export default function ProductosCRUD({ role = 'admin' }: { role?: 'admin' | 'stock' | 'pedidos' | 'client' }) {
  const navigate = useNavigate();
  const readOnly = role === 'client';
  const isStockMode = role === 'stock';
  const isAuth = !!getAccessToken();
  const hideCreate = role !== 'admin';
  const hideDelete = role === 'client' || role === 'stock';
  const hideRelations = role === 'client' || role === 'stock';
  const hideCategoriasBtn = role === 'client' || role === 'stock';
  const hideExport = role === 'client' || role === 'stock';
  const [state, dispatch] = useReducer(reducer, init);
  const [ingPopup, setIngPopup] = useState<{ id: number; nombre: string } | null>(null);
  const [catPopup, setCatPopup] = useState<{ id: number; nombre: string } | null>(null);
  const [allCats, setAllCats] = useState<Categoria[]>([]);
  const [allIngs, setAllIngs] = useState<Ingrediente[]>([]);
  const [showVariantesModal, setShowVariantesModal] = useState(false);
  const [recentlyAdded, setRecentlyAdded] = useState<Set<number>>(new Set());
  const addTimerRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  /** Adds a product to the cart (localStorage) and shows visual feedback. */
  const handleAddToCart = (prod: Producto) => {
    addToCart(prod.id, prod.nombre, Number(prod.precio_base));
    triggerFeedback(prod.id);
  };

  /**
   * Visual feedback: changes the "Agregar al carrito" button to green
   * with a checkmark for 1.2 seconds, then reverts.
   * Uses a ref map to manage per-product timers.
   */
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

  // Load all categories and ingredients for the relationship selectors
  useEffect(() => {
    if (hideRelations) return;
    categoriasApi.getAll(0, 1000).then(setAllCats).catch(() => {});
    ingredientesApi.getAll(0, 1000).then(setAllIngs).catch(() => {});
  }, [hideRelations]);

  // Load selected categories and ingredients when editing an existing product
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

  /**
   * Fetches the current page of products from the backend.
   * After fetching, auto-corrects products with stock=0 but disponible=true
   * (only for non-readonly roles).
   */
  const fetchData = useCallback(async () => {
    dispatch({ type: "SET_LOADING", payload: true });
    try {
      const data = await productosApi.getAll(state.page * PAGE_SIZE, PAGE_SIZE);
      dispatch({ type: "SET_ITEMS", payload: data });

      // Auto-correct products with stock=0 but disponible=true
      // Only if the user has write permissions (not client)
      if (!readOnly) {
        const toFix = data.filter((p) => p.stock_cantidad === 0 && p.disponible === true);
        for (const prod of toFix) {
          try {
            await productosApi.update(prod.id, { disponible: false });
          } catch {
            // Silently skip if the user lacks permissions
          }
        }
        if (toFix.length > 0) {
          // Reload to reflect the changes
          const freshData = await productosApi.getAll(state.page * PAGE_SIZE, PAGE_SIZE);
          dispatch({ type: "SET_ITEMS", payload: freshData });
        }
      }
    } catch (e) {
      dispatch({ type: "SET_ERROR", payload: (e as Error).message });
    }
  }, [state.page, readOnly]);

  useEffect(() => { fetchData(); }, [fetchData]);

  /**
   * Syncs calculated price from selected ingredients (create mode only).
   * When ingredients are selected, the precio_base is auto-computed as the
   * sum of all ingredient prices, and the manual price input is disabled.
   */
  const precioCalculadoRef = useRef(0);
  useEffect(() => {
    if (!state.editingId && state.selectedIngredientes.length > 0) {
      const total = state.selectedIngredientes.reduce((sum, ing) => {
        const fullIng = allIngs.find(a => a.id === ing.id);
        return sum + Number(fullIng?.precio_actual ?? 0);
      }, 0);
      precioCalculadoRef.current = total;
      form.setFieldValue('precio_base', total);
    }
  }, [state.selectedIngredientes, state.editingId, allIngs]);

  /**
   * TanStack Form for creating/editing a single product.
   *
   * Submit behavior depends on state:
   *   - editingId + stockEditOnly: only updates stock_cantidad + disponible.
   *   - editingId (full): updates all fields.
   *   - No editingId (create): creates with categorias_ids + ingredientes.
   *
   * Error handling extracts the backend's detail field (AxiosError).
   */
  const form = useAppForm<ProductoCreate>({
    defaultValues: {
      nombre: "",
      descripcion: "",
      precio_base: 0,
      receta: "",
      stock_cantidad: 0,
      tiempo_prep_min: 0,
      disponible: true,
      imagenes_url: [],
      categorias_ids: [],
      ingredientes: [],
    },
    onSubmit: async ({ value }) => {
      try {
        if (state.editingId) {
          if (state.stockEditOnly) {
            await productosApi.update(state.editingId, {
              stock_cantidad: value.stock_cantidad,
              disponible: value.disponible,
            });
          } else {
            await productosApi.update(state.editingId, {
              nombre: value.nombre,
              descripcion: value.descripcion,
              receta: value.receta,
              precio_base: value.precio_base,
              stock_cantidad: value.stock_cantidad,
              disponible: value.disponible,
            });
          }
        } else {
          // Guard: require a positive price when no ingredients are selected
          if (state.selectedIngredientes.length === 0 && value.precio_base <= 0) {
            dispatch({ type: "SET_ERROR", payload: "El precio base debe ser mayor a 0 cuando no hay ingredientes" });
            return;
          }
          await productosApi.create({
            ...value,
            categorias_ids: state.selectedCategorias.map(c => c.id),
            ingredientes: state.selectedIngredientes.map(i => ({
              ingrediente_id: i.id,
              es_removible: true,
              es_principal: false,
              orden: 0,
            })),
          });
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
    },
  });

  // Action wrappers that combine TanStack Form + reducer

  /** Opens the form in create mode with blank defaults. */
  const handleStartCreate = () => {
    form.reset();
    dispatch({ type: "START_CREATE" });
  };

  /** Opens the form in edit mode, pre-filled with the product's current values. */
  const handleStartEdit = (prod: Producto) => {
    form.reset({
      nombre: prod.nombre,
      descripcion: prod.descripcion ?? "",
      receta: prod.receta ?? "",
      precio_base: prod.precio_base,
      stock_cantidad: prod.stock_cantidad,
      tiempo_prep_min: prod.tiempo_prep_min,
      disponible: prod.disponible,
      imagenes_url: prod.imagenes_url,
    });
    dispatch({ type: "START_EDIT", payload: prod });
  };

  /** Opens the form in stock-only edit mode. */
  const handleStartStockEdit = (prod: Producto) => {
    form.reset({
      nombre: prod.nombre,
      descripcion: prod.descripcion ?? "",
      receta: prod.receta ?? "",
      precio_base: prod.precio_base,
      stock_cantidad: prod.stock_cantidad,
      tiempo_prep_min: prod.tiempo_prep_min,
      disponible: prod.disponible,
      imagenes_url: prod.imagenes_url,
    });
    dispatch({ type: "START_STOCK_EDIT", payload: prod });
  };

  /** Closes the form and resets all editing state. */
  const handleCloseForm = () => {
    form.reset();
    dispatch({ type: "CLOSE_FORM" });
  };

  /** Deletes a product after user confirmation. */
  const handleDelete = async (id: number) => {
    if (!confirm("Eliminar este producto?")) return;
    try {
      await productosApi.delete(id);
      fetchData();
    } catch (err) {
      dispatch({ type: "SET_ERROR", payload: (err as Error).message });
    }
  };

  /** Client-side filter: by name, and for clients, hide unavailable products. */
  const filtered = state.items.filter((p) =>
    (role !== 'client' || p.disponible === true) &&
    p.nombre.toLowerCase().includes(state.filter.toLowerCase())
  );

  // ---- RENDER ----

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">{role === 'client' ? 'Menu' : 'Gestion de Productos'}</h1>
      {state.error && <p className="text-red-500 mb-4">{state.error}</p>}

      {/* Toolbar: create buttons, filter, export */}
      <div className="flex gap-2 mb-4 items-center">
        {!hideCreate && (
          <button onClick={handleStartCreate}
            className="bg-green-600 text-white px-4 py-1 rounded cursor-pointer">Crear Producto</button>
        )}
        {!hideCreate && (
          <button onClick={() => setShowVariantesModal(true)}
            className="bg-indigo-600 text-white px-4 py-1 rounded cursor-pointer">Crear Variantes</button>
        )}
        <input type="text" placeholder="Filtrar por nombre..." value={state.filter}
          onChange={(e) => dispatch({ type: "SET_FILTER", payload: e.target.value })}
          className="border px-2 py-1 rounded flex-grow" />
        {!hideExport && (
          <button onClick={() => exportToExcel(filtered.map(({ id, nombre, precio_base, stock_cantidad, disponible, tiempo_prep_min }) => ({
              id, nombre, precio_base, stock_cantidad, tiempo_prep_min, disponible: disponible ? "Si" : "No",
            })), "productos")}
            className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Exportar Excel</button>
        )}
      </div>

      {/* Create/edit form (visible when showForm is active) */}
      {state.showForm && (!hideCreate || state.stockEditOnly) && (
        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="border p-4 mb-4 rounded bg-gray-50">
          {state.stockEditOnly ? (
            /* Stock-only mode: just stock_cantidad + disponible */
            <div className="grid grid-cols-2 gap-4 mb-4">
              <form.Field name="stock_cantidad">
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Stock</label>
                    <input type="number" min="0"
                      value={field.state.value ?? 0}
                      onChange={(e) => field.handleChange(Number(e.target.value))}
                      onBlur={field.handleBlur}
                      className="border px-2 py-1 rounded w-full" />
                  </div>
                )}
              </form.Field>
              <form.Field name="disponible">
                {(field) => (
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Disponible</label>
                    <input type="checkbox" checked={field.state.value ?? true}
                      onChange={(e) => field.handleChange(e.target.checked)} />
                  </div>
                )}
              </form.Field>
            </div>
          ) : (
            /* Full create/edit form */
            <div className="grid grid-cols-2 gap-4 mb-4">
              <form.Field name="nombre">
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Nombre</label>
                    <input value={field.state.value}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      className="border px-2 py-1 rounded w-full" required />
                  </div>
                )}
              </form.Field>
              <form.Field name="descripcion">
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Descripcion</label>
                    <input value={field.state.value ?? ""}
                      onChange={(e) => field.handleChange(e.target.value)}
                      onBlur={field.handleBlur}
                      className="border px-2 py-1 rounded w-full" />
                  </div>
                )}
              </form.Field>
              <div>
                <label className="block text-sm font-medium">Precio Base</label>
                {(() => {
                  const editingProduct = state.editingId ? state.items.find(p => p.id === state.editingId) : null;
                  const hasIngredients = editingProduct?.tiene_ingredientes ?? false;
                  // Disabled when ingredients are assigned (price is auto-calculated)
                  const precioDisabled = state.editingId ? hasIngredients : state.selectedIngredientes.length > 0;
                  return (
                    <form.Field name="precio_base">
                      {(field) => (
                        <>
                          <input type="number" step="0.01" value={field.state.value ?? 0}
                            disabled={precioDisabled}
                            onChange={(e) => field.handleChange(Number(e.target.value))}
                            onBlur={field.handleBlur}
                            className={`border px-2 py-1 rounded w-full ${precioDisabled ? 'bg-gray-200 text-gray-400 cursor-not-allowed' : ''}`} />
                          {(state.editingId && hasIngredients) || (!state.editingId && state.selectedIngredientes.length > 0) ? (
                            <p className="text-xs text-gray-500 mt-1 italic">
                              {!state.editingId
                                ? `Calculado desde ${state.selectedIngredientes.length} ingrediente(s)`
                                : 'Calculado desde ingredientes'}
                            </p>
                          ) : null}
                        </>
                      )}
                    </form.Field>
                  );
                })()}
              </div>
              {/* Recipe textarea */}
              <div className="col-span-2">
                <form.Field name="receta">
                  {(field) => (
                    <div>
                      <label className="block text-sm font-medium mb-1">Receta / Preparacion</label>
                      <textarea
                        value={field.state.value ?? ""}
                        onChange={(e) => field.handleChange(e.target.value)}
                        onBlur={field.handleBlur}
                        rows={4}
                        placeholder="Ej: 200 g de harina, 2 huevos, 1 taza de leche. Mezclar y cocinar a fuego medio..."
                        className="w-full border border-gray-300 px-3 py-2 rounded text-sm"
                      />
                    </div>
                  )}
                </form.Field>
              </div>
              <form.Field name="stock_cantidad">
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Stock</label>
                    <input type="number" min="0" value={field.state.value ?? 0}
                      onChange={(e) => field.handleChange(Number(e.target.value))}
                      onBlur={field.handleBlur}
                      className="border px-2 py-1 rounded w-full" />
                  </div>
                )}
              </form.Field>
              <form.Field name="tiempo_prep_min">
                {(field) => (
                  <div>
                    <label className="block text-sm font-medium">Tiempo Prep. (min)</label>
                    <input type="number" value={field.state.value ?? 0}
                      onChange={(e) => field.handleChange(Number(e.target.value))}
                      onBlur={field.handleBlur}
                      className="border px-2 py-1 rounded w-full" />
                  </div>
                )}
              </form.Field>
              <form.Field name="disponible">
                {(field) => (
                  <div className="flex items-center gap-2">
                    <label className="text-sm font-medium">Disponible</label>
                    <input type="checkbox" checked={field.state.value ?? true}
                      onChange={(e) => field.handleChange(e.target.checked)} />
                  </div>
                )}
              </form.Field>
            </div>
          )}

          {/* Category and ingredient selectors (create mode only, admin/pedidos) */}
          {!state.editingId && !hideCreate && !isStockMode && (
            <>
              <div className="border p-4 mb-4 rounded bg-gray-50">
                <h3 className="text-lg font-medium mb-2">Categorias</h3>
                {state.selectedCategorias.length > 0 && (
                  <table className="w-full border-collapse border mb-2">
                    <thead><tr className="bg-gray-200">
                      <th className="border p-2 text-left">Nombre</th>
                      <th className="border p-2 text-left">Descripcion</th>
                      <th className="border p-2 text-left">Accion</th>
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
                <button type="button" onClick={() => dispatch({ type: "SET_SHOW_CATEGORIA_SELECTOR", payload: true })} className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Seleccionar Categorias</button>
              </div>

              <div className="border p-4 mb-4 rounded bg-gray-50">
                <h3 className="text-lg font-medium mb-2">
                  Insumos
                </h3>
                {state.selectedIngredientes.length > 0 && (
                  <table className="w-full border-collapse border mb-2">
                    <thead><tr className="bg-gray-200">
                      <th className="border p-2 text-left">Nombre</th>
                      <th className="border p-2 text-left">Alergeno</th>
                      <th className="border p-2 text-left">Accion</th>
                    </tr></thead>
                    <tbody>
                      {state.selectedIngredientes.map((i) => (
                        <tr key={i.id}>
                          <td className="border p-2">{i.nombre}</td>
                          <td className="border p-2">{i.es_alergeno ? "Si" : "No"}</td>
                          <td className="border p-2">
                            <button type="button" onClick={() => dispatch({ type: "SET_SELECTED_INGREDIENTES", payload: state.selectedIngredientes.filter(si => si.id !== i.id) })} className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer">Quitar</button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <button type="button"
                  onClick={() => dispatch({ type: "SET_SHOW_INGREDIENTE_SELECTOR", payload: true })}
                  className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer">Seleccionar Insumos</button>
              </div>
            </>
          )}

          {/* Form action buttons */}
          <div className="flex gap-2 mt-4">
            <button type="submit" disabled={form.state.isSubmitting}
              className="bg-blue-600 text-white px-4 py-1 rounded cursor-pointer disabled:opacity-50">
              {form.state.isSubmitting ? "Guardando..." : (state.stockEditOnly ? "Actualizar Stock" : (state.editingId ? "Actualizar" : "Crear"))}</button>
            <button type="button" onClick={handleCloseForm}
              className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer">Cancelar</button>
          </div>
        </form>
      )}

      {/* Product list table */}
      {state.loading ? <p>Cargando...</p> : (
        <table className="w-full border-collapse border">
          <thead><tr className="bg-gray-200">
            {!readOnly && <th className="border p-2 text-left">ID</th>}
            <th className="border p-2 text-left">Nombre</th>
            <th className="border p-2 text-left">Precio</th>
            {!readOnly && <th className="border p-2 text-left">Stock</th>}
            {!readOnly && !isStockMode && <th className="border p-2 text-left">Prep (min)</th>}
            <th className="border p-2 text-left">Disponible</th>
            {!readOnly && (!isStockMode || role === 'stock') && (
              <th className="border p-2 text-left">{isStockMode ? 'Ingredientes' : 'Relaciones'}</th>
            )}
            {!readOnly && (
              <th className="border p-2 text-left">Acciones</th>
            )}
                {isAuth && role !== 'stock' && <th className="border p-2 text-left">Agregar al carrito</th>}
          </tr></thead>
          <tbody>
            {filtered.map((prod) => (
              <tr key={prod.id} className="hover:bg-gray-100">
                {!readOnly && <td className="border p-2">{prod.id}</td>}
                <td className="border p-2">{prod.nombre}</td>
                <td className="border p-2">
                  <span>
                    ${Number(prod.precio_base).toFixed(2)}
                    {prod.tiene_ingredientes && role !== 'client' && (
                      <span className="text-xs text-blue-600 font-medium ml-1">(calc)</span>
                    )}
                  </span>
                </td>
                {!readOnly && (
                  <td className="border p-2">
                    <span className={`font-mono font-semibold ${prod.stock_cantidad === 0 ? 'text-red-600' : 'text-green-700'}`}>
                      {prod.stock_cantidad}
                    </span>
                  </td>
                )}
                {!readOnly && !isStockMode && <td className="border p-2">{prod.tiempo_prep_min}</td>}
                <td className="border p-2">
                  <span className={`font-medium ${prod.disponible ? 'text-green-700' : 'text-red-600'}`}>
                    {prod.disponible ? "Si" : "No"}
                  </span>
                </td>
                {!readOnly && (!isStockMode || role === 'stock') && (
                  <td className="border p-2">
                    <div className="flex gap-1">
                      <button onClick={() => setIngPopup({ id: prod.id, nombre: prod.nombre })}
                        className="bg-purple-600 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-purple-700">Insumos</button>
                      {!hideCategoriasBtn && (
                        <button onClick={() => setCatPopup({ id: prod.id, nombre: prod.nombre })}
                          className="bg-teal-600 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-teal-700">Categorias</button>
                      )}
                    </div>
                  </td>
                )}
                {!readOnly && (
                  <td className="border p-2">
                    <div className="flex gap-1 flex-wrap">
                      {!isStockMode && (
                        <button onClick={() => handleStartEdit(prod)}
                          className="bg-yellow-500 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-yellow-600">Editar</button>
                      )}
                      <button onClick={() => handleStartStockEdit(prod)}
                        className="bg-amber-700 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-amber-800">Gestionar Stock</button>
                      {!isStockMode && !hideDelete && (
                        <button onClick={() => handleDelete(prod.id)}
                          className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-red-700">Eliminar</button>
                      )}
                    </div>
                  </td>
                )}
                {isAuth && role !== 'stock' && (
                  <td className="border p-2">
                    {(() => {
                      let addable = true;
                      let disabledReason = '';

                      if (!prod.disponible) {
                        addable = false;
                        disabledReason = 'No disponible';
                      } else if (prod.stock_cantidad <= 0) {
                        addable = false;
                        disabledReason = 'Sin stock';
                      }

                      if (!addable) {
                        return (
                          <button
                            disabled
                            className="px-2 py-1 rounded text-sm bg-gray-400 text-gray-700 cursor-not-allowed"
                            title={disabledReason}
                          >
                            {disabledReason}
                          </button>
                        );
                      }

                      return (
                        <button
                          onClick={() => handleAddToCart(prod)}
                          className={`px-2 py-1 rounded text-sm cursor-pointer transition-colors ${
                            recentlyAdded.has(prod.id)
                              ? "bg-green-600 text-white"
                              : "bg-blue-600 text-white hover:bg-blue-700"
                          }`}
                        >
                          {recentlyAdded.has(prod.id) ? "OK Agregado" : "Agregar al carrito"}
                        </button>
                      );
                    })()}
                  </td>
                )}
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={readOnly ? 4 : (isStockMode ? 7 : isAuth ? 9 : 8)} className="border p-2 text-center text-gray-500">Sin resultados</td></tr>}
          </tbody>
        </table>
      )}

      {/* Pagination + cart button */}
      <div className="flex gap-2 mt-4 items-center justify-between">
        <div className="flex gap-2 items-center">
          <button disabled={state.page === 0}
            onClick={() => dispatch({ type: "SET_PAGE", payload: state.page - 1 })}
            className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer">Anterior</button>
          <span>Pagina {state.page + 1}</span>
          <button disabled={state.items.length < PAGE_SIZE}
            onClick={() => dispatch({ type: "SET_PAGE", payload: state.page + 1 })}
            className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer">Siguiente</button>
        </div>
        {isAuth && role !== 'stock' && (
          <button
            onClick={() => navigate("/carrito")}
            className="bg-green-700 text-white px-4 py-1.5 rounded text-sm font-semibold hover:bg-green-800 cursor-pointer"
          >
            Ver Carrito {getItemCount() > 0 ? `(${getItemCount()})` : ""}
          </button>
        )}
      </div>

      {/* Popups for ingredient and category management */}
      {ingPopup && <IngredientesPopup productoId={ingPopup.id} productoNombre={ingPopup.nombre} onClose={() => setIngPopup(null)} />}
      {catPopup && <CategoriasPopup productoId={catPopup.id} productoNombre={catPopup.nombre} onClose={() => setCatPopup(null)} />}
      {showVariantesModal && (
        <CrearVariantesModal
          allCategorias={allCats}
          onClose={() => setShowVariantesModal(false)}
          onComplete={() => { fetchData(); }}
        />
      )}

      {/* Category selector for creation form */}
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

      {/* Ingredient selector for creation form */}
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

    </div>
  );
}
