/**
 * ProductosCliente — Client-facing product listing page with card grid layout.
 *
 * Responsibilities:
 *  - Fetch all products on mount via productosApi.getAll()
 *  - Client-side text filter by name
 *  - Hide products where disponible === false
 *  - Simple prev/next pagination (PAGE_SIZE = 12 for 3 rows of 4)
 *  - Renders each product via ProductCard with add-to-cart integration
 *  - Shows "Ver Carrito (N)" button for authenticated users
 *
 * State management: useReducer for data grid (same pattern as ProductosCRUD).
 * Visual feedback: recently-added Set with useRef timers (matching ProductosCRUD).
 */
import { useReducer, useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { productosApi } from "../api/productos";
import type { Producto } from "../api/productos";
import { useCartStore } from "../store/cartStore";
import { getAccessToken } from "../api/client";
import ProductCard from "./ProductCard";

const PAGE_SIZE = 12;

// ── State ──

interface State {
  items: Producto[];
  loading: boolean;
  error: string | null;
  page: number;
  filter: string;
}

type Action =
  | { type: "SET_ITEMS"; payload: Producto[] }
  | { type: "SET_LOADING"; payload: boolean }
  | { type: "SET_ERROR"; payload: string | null }
  | { type: "SET_PAGE"; payload: number }
  | { type: "SET_FILTER"; payload: string };

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
};

// ── Page component ──

export default function ProductosCliente() {
  const navigate = useNavigate();
  const [state, dispatch] = useReducer(reducer, init);
  const isAuth = !!getAccessToken();

  // Recently-added feedback (matching ProductosCRUD pattern)
  const [recentlyAdded, setRecentlyAdded] = useState<Set<number>>(new Set());
  const addTimerRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  /** Adds a product to the cart and triggers visual feedback. */
  const handleAddToCart = (prod: Producto) => {
    useCartStore.getState().addToCart(prod.id, prod.nombre, Number(prod.precio_base));
    triggerFeedback(prod.id);
  };

  /**
   * Visual feedback: turns the button green for 1.2s, then reverts.
   * Uses a ref map to manage per-product timers independently.
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

  /**
   * Fetches all products on mount.
   * Uses a large limit (1000) to get everything; filtering/pagination is client-side.
   */
  const fetchData = useCallback(async () => {
    dispatch({ type: "SET_LOADING", payload: true });
    try {
      const data = await productosApi.getAll(0, 1000);
      dispatch({ type: "SET_ITEMS", payload: data });
    } catch (e) {
      dispatch({ type: "SET_ERROR", payload: (e as Error).message });
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ── Derived data ──

  /** Filter: only available products matching the text filter. */
  const filtered = state.items.filter(
    (p) => p.disponible === true && p.nombre.toLowerCase().includes(state.filter.toLowerCase())
  );

  /** Current page slice. */
  const paged = filtered.slice(state.page * PAGE_SIZE, (state.page + 1) * PAGE_SIZE);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);

  // ── Render ──

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Menu</h1>

      {/* Error state */}
      {state.error && <p className="text-red-500 mb-4">{state.error}</p>}

      {/* Search filter */}
      <div className="flex gap-2 mb-4 items-center">
        <input
          type="text"
          placeholder="Filtrar por nombre..."
          value={state.filter}
          onChange={(e) => dispatch({ type: "SET_FILTER", payload: e.target.value })}
          className="border px-2 py-1 rounded flex-grow"
        />
      </div>

      {/* Loading state */}
      {state.loading ? (
        <p className="text-center text-gray-500 py-8">Cargando...</p>
      ) : state.error ? null : filtered.length === 0 ? (
        /* Empty state */
        <p className="text-center text-gray-500 py-8">Sin resultados</p>
      ) : (
        <>
          {/* Product grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {paged.map((prod) => (
              <ProductCard
                key={prod.id}
                product={prod}
                onAddToCart={handleAddToCart}
                recentlyAdded={recentlyAdded}
              />
            ))}
          </div>

          {/* Pagination + cart button */}
          <div className="flex gap-2 mt-6 items-center justify-between">
            <div className="flex gap-2 items-center">
              <button
                disabled={state.page === 0}
                onClick={() => dispatch({ type: "SET_PAGE", payload: state.page - 1 })}
                className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer"
              >
                Anterior
              </button>
              <span>
                Pagina {state.page + 1}{totalPages > 1 ? ` de ${totalPages}` : ""}
              </span>
              <button
                disabled={state.page + 1 >= totalPages}
                onClick={() => dispatch({ type: "SET_PAGE", payload: state.page + 1 })}
                className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer"
              >
                Siguiente
              </button>
            </div>

            {isAuth && (
              <button
                onClick={() => navigate("/carrito")}
                className="bg-green-700 text-white px-4 py-1.5 rounded text-sm font-semibold hover:bg-green-800 cursor-pointer"
              >
                Ver Carrito {useCartStore.getState().getItemCount() > 0 ? `(${useCartStore.getState().getItemCount()})` : ""}
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
