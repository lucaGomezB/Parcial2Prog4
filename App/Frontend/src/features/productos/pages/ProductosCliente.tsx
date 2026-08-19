/**
 * ProductosCliente — Client-facing product listing page with card grid layout.
 *
 * Responsibilities:
 *  - Fetch all products via TanStack Query useProductos()
 *  - Fetch categories for filter chips
 *  - Client-side text filter by name and category filter
 *  - Hide products where disponible === false
 *  - Simple prev/next pagination (PAGE_SIZE = 12 for 3 rows of 4)
 *  - Renders each product via ProductCard with add-to-cart integration
 *  - Shows "Ver Carrito (N)" button for authenticated users
 *  - Skeleton loaders while fetching
 */
import { useRef, useState, useMemo, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { Producto } from "@/features/productos/api/productos";
import { useProductos } from "@/features/productos/hooks/useProductos";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { categoriasApi } from "@/features/categorias/api/categorias";
import type { CategoriaTree } from "@/features/categorias/api/categorias";
import { getDescendantIds } from "@/features/categorias/utils/tree";
import { useCartStore, useCartItems } from "@/shared/store/cartStore";
import { getAccessToken, getUserRoles } from "@/shared/api/client";
import { addToast } from "@/shared/components/Toast";
import { STOCK_EXCEEDED_MESSAGE } from "@/shared/constants/cartMessages";
import ProductCard from "@/features/productos/components/ProductCard";
import SearchFilter from "@/shared/components/SearchFilter";
import { useDisponibilidadCarrito } from "@/features/productos/hooks/useDisponibilidadCarrito";
import { pedidosApi } from "@/features/pedidos/api/pedidos";

const PAGE_SIZE = 12;

/**
 * Skeleton loader grid — mimics the exact layout of product cards
 * but with animated pulse placeholders. Uses the same responsive grid.
 */
function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="bg-white rounded-lg shadow-md overflow-hidden animate-pulse">
          <div className="w-full aspect-[4/3] bg-gray-200" />
          <div className="p-4 space-y-2">
            <div className="h-4 bg-gray-200 rounded w-3/4" />
            <div className="h-3 bg-gray-200 rounded w-1/2" />
            <div className="h-6 bg-gray-200 rounded w-1/3 mt-2" />
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Flattens the category tree into a depth-annotated list for single-pass rendering.
 * All chips render as siblings in one flex container — no nested divs breaking flow.
 */
function flattenTree(nodes: CategoriaTree[], depth = 0): Array<{ node: CategoriaTree; depth: number }> {
  const flat: Array<{ node: CategoriaTree; depth: number }> = [];
  for (const node of nodes) {
    flat.push({ node, depth });
    if (node.subcategorias.length > 0) {
      flat.push(...flattenTree(node.subcategorias, depth + 1));
    }
  }
  return flat;
}

// ── Page component ──

export default function ProductosCliente() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isAuth = !!getAccessToken();
  const esAdmin = getUserRoles().includes("ADMIN");

  // UI-only state (declared before useProductos — needed for query key)
  const [page, setPage] = useState(0);
  const [filter, setFilter] = useState("");
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<Set<number>>(new Set());

  // Derive array from Set for API calls
  const selectedIdsArray = useMemo(() => Array.from(selectedCategoryIds), [selectedCategoryIds]);

  // TanStack Query: products — server-side filtering by categories (multi-select)
  const { data: productsData, isLoading, isError, error } = useProductos(
    0, 1000, undefined, selectedIdsArray.length > 0 ? selectedIdsArray : undefined,
    undefined, undefined, { refetchInterval: 15_000 }
  );
  const products = productsData?.items ?? [];

  // TanStack Query: categories (for filter chips + image fallback)
  const { data: categoriasData } = useQuery({
    queryKey: ["categorias", "tree"],
    queryFn: () => categoriasApi.getTree(),
  });
  const categorias = categoriasData ?? [];

  // Cart items (reactive) + per-product addable availability given the cart.
  // Disponibilidad accounts for SHARED ingredients across products, so a
  // product can become unavailable when another cart item consumes its shared
  // ingredient. Refetches whenever the cart or product list changes.
  const cartItems = useCartItems();
  const productIds = useMemo(() => products.map((p) => p.id), [products]);
  const { data: disponibilidadData } = useDisponibilidadCarrito(
    productIds,
    cartItems.map((i) => ({ productoId: i.productoId, cantidad: i.cantidad })),
  );
  const disponibilidadMap = useMemo(() => {
    const map: Record<number, number> = {};
    for (const p of disponibilidadData?.productos ?? []) {
      map[p.producto_id] = p.agregable;
    }
    return map;
  }, [disponibilidadData]);

  // Quantity of each product already in the cart (productoId -> cantidad).
  const cartQtyMap = useMemo(() => {
    const map: Record<number, number> = {};
    for (const item of cartItems) {
      map[item.productoId] = item.cantidad;
    }
    return map;
  }, [cartItems]);

  const limitantesMap = useMemo(() => {
    const map: Record<number, string[]> = {};
    for (const p of disponibilidadData?.productos ?? []) {
      map[p.producto_id] = (p.limitantes ?? []).map((l) => l.nombre);
    }
    return map;
  }, [disponibilidadData]);

  // Tracks the pre-add availability map + the product just added, so we can
  // notify (yellow toast) when an add exhausts a SHARED ingredient and makes
  // another product impossible to load.
  const pendingAddRef = useRef<{ before: Record<number, number>; addedId: number } | null>(null);

  useEffect(() => {
    const pending = pendingAddRef.current;
    if (!pending) return;
    pendingAddRef.current = null;
    for (const p of products) {
      if (p.id === pending.addedId) continue;
      const before = pending.before[p.id] ?? p.stock_cantidad;
      const after = disponibilidadMap[p.id] ?? p.stock_cantidad;
      if (before > 0 && after <= 0) {
        addToast("warn", `Se ha acabado el stock disponible para ${p.nombre}`);
      }
    }
  }, [disponibilidadMap, products]);

  // Recently-added feedback
  const [recentlyAdded, setRecentlyAdded] = useState<Set<number>>(new Set());
  const addTimerRef = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());

  /** Guard against double-fire on the async add (product ID -> in-flight). */
  const addingRef = useRef<Set<number>>(new Set());

  /** Adds a product to the cart, validating SHARED ingredient stock first.
   *  Guests are redirected to /login?mode=register to create an account first. */
  const handleAddToCart = async (prod: Producto) => {
    if (!isAuth) {
      navigate("/login?mode=register");
      return;
    }
    if (addingRef.current.has(prod.id)) return;
    addingRef.current.add(prod.id);
    try {
      // Fast synchronous pre-check (own derived stock)
      const currentCartItem = useCartStore.getState().items.find((i) => i.productoId === prod.id);
      const currentCartQty = currentCartItem?.cantidad ?? 0;
      if (currentCartQty + 1 > prod.stock_cantidad) {
        addToast("error", STOCK_EXCEEDED_MESSAGE);
        return;
      }

      // Synchronous shared-aware check: if this product can't be added right now
      // (agregable <= 0 because a shared ingredient was already consumed by an
      // earlier-added product), block immediately — earlier products keep priority.
      const agregable = disponibilidadMap[prod.id] ?? prod.stock_cantidad;
      if (agregable <= 0) {
        addToast("error", "No nos alcanza el stock para agregar este producto.");
        return;
      }

      // Shared-ingredient validation against the proposed cart (current + 1).
      try {
        const proposed = useCartStore.getState().items.map((i) => ({
          producto_id: i.productoId,
          cantidad: i.productoId === prod.id ? i.cantidad + 1 : i.cantidad,
        }));
        if (!proposed.some((p) => p.producto_id === prod.id)) {
          proposed.push({ producto_id: prod.id, cantidad: 1 });
        }
        const validation = await pedidosApi.validarStock({ detalles: proposed });
        if (!validation.valido) {
          addToast("error", "No nos alcanza el stock para agregar este producto.");
          return;
        }
      } catch {
        // Validation failed (e.g. network) — block the add rather than risk
        // exceeding shared stock and blocking the cart.
        addToast("error", "No pudimos validar el stock. Intentalo de nuevo.");
        return;
      }

      const result = useCartStore.getState().addToCart(
        prod.id, prod.nombre, Number(prod.precio_actual || prod.precio_base), 1, prod.stock_cantidad,
      );
      if (!result.success) {
        addToast("error", STOCK_EXCEEDED_MESSAGE);
        return;
      }

      // Capture the pre-add availability so the notification effect can detect
      // products that just became impossible due to this add.
      pendingAddRef.current = { before: disponibilidadMap, addedId: prod.id };

      // Recompute availability immediately against the resulting cart so products
      // that became un-addable (agregable = 0, shared ingredient exhausted) are
      // marked "No disponible" right away instead of after the stale refetch
      // window. Prefix match invalidates every ['pedidos','disponibilidad',...] key.
      queryClient.invalidateQueries({ queryKey: ['pedidos', 'disponibilidad'] });

      addToast("exito", `${prod.nombre} agregado al carrito`);
      triggerFeedback(prod.id);
    } finally {
      addingRef.current.delete(prod.id);
    }
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

  // Category images map for product card fallback
  const categoryImagesMap = useMemo(() => {
    const map: Record<number, string[]> = {};
    for (const cat of categorias) {
      if (cat.imagen_url && cat.imagen_url.length > 0) {
        map[cat.id] = cat.imagen_url;
      }
    }
    return map;
  }, [categorias]);

  // ── Empty category filter ──

  /**
   * Persisted set of category IDs that have at least one product assigned.
   * Computed when viewing "Todas" (full product list) and preserved via useRef
   * so it survives across re-renders when filters change.
   */
  const nonEmptyCategoryIds = useRef<Set<number>>(new Set());

  useEffect(() => {
    if (selectedCategoryIds.size === 0 && products.length > 0) {
      const ids = new Set<number>();
      for (const p of products) {
        for (const cid of p.categoria_ids) {
          ids.add(cid);
        }
      }
      nonEmptyCategoryIds.current = ids;
    }
  }, [selectedCategoryIds.size, products]);

  // ── Category ID → node lookup map (O(1) for getDescendantIds) ──
  const categoryMap = useRef<Map<number, CategoriaTree>>(new Map());

  useEffect(() => {
    const map = new Map<number, CategoriaTree>();
    function indexTree(nodes: CategoriaTree[]) {
      for (const node of nodes) {
        map.set(node.id, node);
        if (node.subcategorias.length > 0) indexTree(node.subcategorias);
      }
    }
    indexTree(categorias);
    categoryMap.current = map;
  }, [categorias]);

  /**
   * Recursively removes categories that have zero products assigned.
   * If nonEmptyIds is empty (not yet computed), returns nodes unchanged as fallback.
   */
  function filterEmptyCategories(nodes: CategoriaTree[], nonEmptyIds: Set<number>): CategoriaTree[] {
    if (nonEmptyIds.size === 0) return nodes; // fallback: show all
    return nodes
      .filter(node =>
        nonEmptyIds.has(node.id) ||
        node.subcategorias.some(child => nonEmptyIds.has(child.id))
      )
      .map(node => ({
        ...node,
        subcategorias: filterEmptyCategories(node.subcategorias, nonEmptyIds),
      }));
  }

  const displayCategories = filterEmptyCategories(categorias, nonEmptyCategoryIds.current);

  /** Flat list of visible categories with depth — all chips render as siblings in one flex row. */
  const flattenedCategories = useMemo(
    () => flattenTree(displayCategories),
    [displayCategories],
  );

  // ── Derived data ──

  /** Filter: only available products matching the text filter. Category filter is server-side.
   *  Wrapped in useMemo for stable reference and to prevent re-sort on every render. */
  const filtered = useMemo(() =>
    products
      .filter(
        (p) =>
          p.disponible === true &&
          p.nombre.toLowerCase().includes(filter.toLowerCase())
      )
      .sort((a, b) => {
        // Products that can still be added first; unavailable (own or shared
        // ingredient exhausted) last. In-cart products are always treated as
        // addable so they sort to the top. Stable sort preserves API order.
        const aAddable = (disponibilidadMap[a.id] ?? a.stock_cantidad) > 0 || (cartQtyMap[a.id] ?? 0) > 0 ? 1 : 0;
        const bAddable = (disponibilidadMap[b.id] ?? b.stock_cantidad) > 0 || (cartQtyMap[b.id] ?? 0) > 0 ? 1 : 0;
        return bAddable - aAddable;
      }),
    [products, filter, disponibilidadMap, cartQtyMap],
  );

  /** Current page slice. */
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  // ── Stable callback for SearchFilter (avoids re-triggering its useEffect on every render) ──

  // ── Guard: prevents setPage(0) on extraneous SearchFilter re-fires from component remounts ──
  const lastFilterRef = useRef("");

  const handleSearch = useCallback((v: string) => {
    if (lastFilterRef.current !== v) {
      lastFilterRef.current = v;
      setFilter(v);
      setPage(0);
    }
  }, []);

  // ── Navigation helpers with functional state to avoid stale closures ──
  const goNext = () => setPage((prev) => Math.min(prev + 1, totalPages - 1));
  const goPrev = () => setPage((prev) => Math.max(prev - 1, 0));

  // ── Render ──

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Menu</h1>

      {/* Error state */}
      {isError && <p className="text-red-500 mb-4">{(error as Error)?.message || "Error al cargar productos"}</p>}

      {/* Search filter */}
      <div className="flex gap-2 mb-4 items-center">
        <SearchFilter
          onSearch={handleSearch}
          placeholder="Filtrar por nombre..."
        />
      </div>

      {/* Category filter chips — flat list, uniform gap, depth shown via subtle color, empty nodes pruned */}
      {displayCategories.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4 items-center">
          <button
            onClick={() => { setSelectedCategoryIds(new Set()); setPage(0); }}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors cursor-pointer ${
              selectedCategoryIds.size === 0
                ? "bg-blue-600 text-white"
                : "bg-gray-200 text-gray-700 hover:bg-gray-300"
            }`}
          >
            Todas
          </button>
          {flattenedCategories.map(({ node, depth }) => (
            <button
              key={node.id}
              onClick={() => {
                setSelectedCategoryIds(prev => {
                  const next = new Set(prev);
                  const found = categoryMap.current.get(node.id);
                  if (!found) return prev;
                  const descendantIds = getDescendantIds(found);
                  if (next.has(node.id)) {
                    for (const did of descendantIds) next.delete(did);
                  } else {
                    for (const did of descendantIds) next.add(did);
                  }
                  return next;
                });
                setPage(0);
              }}
              className={`px-3 py-1 rounded-full text-sm font-medium transition-colors cursor-pointer ${
                selectedCategoryIds.has(node.id)
                  ? "bg-blue-600 text-white"
                  : depth > 0
                    ? "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
              }`}
            >
              {node.nombre}
            </button>
          ))}
        </div>
      )}

      {/* Loading state — skeleton loaders */}
      {isLoading && <SkeletonGrid />}

      {/* Results */}
      {!isLoading && !isError && filtered.length === 0 && (
        <p className="text-center text-gray-500 py-8">Sin resultados</p>
      )}

      {!isLoading && !isError && filtered.length > 0 && (
        <>
          {/* Product grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {paged.map((prod) => (
              <ProductCard
                key={prod.id}
                product={prod}
                onAddToCart={handleAddToCart}
                recentlyAdded={recentlyAdded}
                categoryImages={
                  prod.categoria_ids.length > 0
                    ? categoryImagesMap[prod.categoria_ids[0]]
                    : undefined
                }
                showId={esAdmin}
                agregable={disponibilidadMap[prod.id]}
                limitantes={limitantesMap[prod.id] ?? []}
                enCarrito={cartQtyMap[prod.id] ?? 0}
              />
            ))}
          </div>

          {/* Pagination + cart button */}
          <div className="flex gap-2 mt-6 items-center justify-between">
            <div className="flex gap-2 items-center">
              <button
                disabled={page === 0}
                onClick={goPrev}
                className="bg-gray-300 px-3 py-1 rounded disabled:opacity-50 cursor-pointer"
              >
                Anterior
              </button>
              <span>
                Pagina {page + 1}{totalPages > 1 ? ` de ${totalPages}` : ""}
              </span>
              <button
                disabled={page + 1 >= totalPages}
                onClick={goNext}
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
