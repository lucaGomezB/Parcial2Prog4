/**
 * ProductoDetail — Customer-facing product detail page at /productos/:id.
 *
 * Displays full product information: images, name, description, receta,
 * price, ingredient list with allergen badges, and an add-to-cart section
 * with quantity selector and removable ingredient checkboxes.
 *
 * States: loading (Skeleton), error, not-found, success.
 */
import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useProducto, useProductoIngredientes } from "@/features/productos/hooks/useProductos";
import { useStockWebSocket } from "@/features/productos/hooks/useStockWebSocket";
import { useDisponibilidadCarrito } from "@/features/productos/hooks/useDisponibilidadCarrito";
import { useCartStore, useCartItems } from "@/shared/store/cartStore";
import { addToast } from "@/shared/components/Toast";
import { STOCK_EXCEEDED_MESSAGE } from "@/shared/constants/cartMessages";
import ImageCarousel from "@/shared/components/ImageCarousel";
import AllergenBadge from "@/features/productos/components/AllergenBadge";
import StockHistorialTab from "@/features/productos/components/StockHistorialTab";
import ErrorBanner from "@/shared/components/ErrorBanner";
import { getAccessToken, getUserRoles } from "@/shared/api/client";
import DecimalInput from "@/shared/components/DecimalInput";
import { formatCurrency } from "@/shared/utils/formatCurrency";

// ── Skeleton loader for the detail page ──

function DetailSkeleton() {
  return (
    <div className="max-w-4xl mx-auto p-4 animate-pulse space-y-6">
      <div className="w-full aspect-[16/9] bg-gray-200 rounded" />
      <div className="space-y-2">
        <div className="h-8 bg-gray-200 rounded w-1/2" />
        <div className="h-4 bg-gray-200 rounded w-3/4" />
        <div className="h-4 bg-gray-200 rounded w-1/3" />
      </div>
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-5 bg-gray-200 rounded w-full" />
        ))}
      </div>
    </div>
  );
}

// ── Page Component ──

export default function ProductoDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const productoId = Number(id);

  // TanStack Query: product data
  const {
    data: product,
    isLoading: productLoading,
    isError: productError,
    error: productErrorObj,
  } = useProducto(productoId);

  // TanStack Query: ingredients
  const {
    data: ingredients = [],
    isLoading: ingredientsLoading,
  } = useProductoIngredientes(productoId);

  // Real-time stock via WebSocket
  const { stock: liveStock, isConnected: wsConnected } = useStockWebSocket(
    isNaN(productoId) ? null : productoId
  );

  // Derived stock: prefer live WS value, fall back to fetched product data
  const currentStock = liveStock !== null ? liveStock : product?.stock_cantidad ?? 0;

  // Shared-aware availability: how many MORE of this product can be added given
  // the current cart (accounts for ingredients shared with other cart items).
  const cartItems = useCartItems();
  const { data: disponibilidadData } = useDisponibilidadCarrito(
    isNaN(productoId) ? [] : [productoId],
    cartItems.map((i) => ({ productoId: i.productoId, cantidad: i.cantidad })),
  );
  const disponibilidad = disponibilidadData?.productos?.find((p) => p.producto_id === productoId);
  const agregable = disponibilidad?.agregable;
  const limitantes = (disponibilidad?.limitantes ?? []).map((l) => l.nombre);
  const effectiveAddable = agregable ?? currentStock;

  // UI state
  const [quantity, setQuantity] = useState(1);
  const [excludedIds, setExcludedIds] = useState<Set<number>>(new Set());
  const [added, setAdded] = useState(false);

  // Role-gate: only clients (no role) and pedidos staff see add-to-cart
  const isClientOrPedidos = (() => {
    const roles = getUserRoles();
    return roles.includes("PEDIDOS") || (!!getAccessToken() && roles.length === 0);
  })();

  // Staff-only content (receta, stock historial) is hidden from clients.
  const isStaff = getUserRoles().some((r) => r === "ADMIN" || r === "STOCK");

  // ── Loading state ──
  if (productLoading) {
    return <DetailSkeleton />;
  }

  // ── Error state ──
  if (productError) {
    return (
      <div className="max-w-4xl mx-auto p-4">
        <ErrorBanner isError={true} error={productErrorObj} message="Error al cargar producto" />
        <div className="text-center mt-4">
          <button
            onClick={() => navigate(-1)}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 cursor-pointer"
          >
            Volver
          </button>
        </div>
      </div>
    );
  }

  // ── Not found state ──
  if (!product) {
    return (
      <div className="max-w-4xl mx-auto p-4 text-center">
        <p className="text-gray-500 text-lg mb-4">Producto no encontrado</p>
        <button
          onClick={() => navigate("/productos")}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 cursor-pointer"
        >
          Ver Menu
        </button>
      </div>
    );
  }

  // ── Derived data ──
  const isUnavailable = !product.disponible || effectiveAddable <= 0;
  // Limited by a SHARED ingredient (has own stock but can't be added right now).
  const isSharedLimited = product.disponible && currentStock > 0 && effectiveAddable <= 0;
  // Three distinct states, each with its own clear label (mirrors ProductCard):
  //   - "No disponible": catalog flag turned off by the admin (permanent).
  //   - "Limitado por tu carrito": a cart item consumed the shared ingredient.
  //   - "Sin stock": own derived stock is zero (transient, ingredient-based).
  const unavailableLabel = !product.disponible
    ? "No disponible"
    : isSharedLimited
      ? "Limitado por tu carrito"
      : "Sin stock";
  const removableIngredients = ingredients.filter((ing) => ing.es_removible);

  const handleToggleExclusion = (ingredienteId: number) => {
    setExcludedIds((prev) => {
      const next = new Set(prev);
      if (next.has(ingredienteId)) {
        next.delete(ingredienteId);
      } else {
        next.add(ingredienteId);
      }
      return next;
    });
  };

  const handleAddToCart = () => {
    // Shared-aware check: cannot add more than the shared ingredients allow.
    if (quantity > effectiveAddable) {
      addToast("error", "No nos alcanza el stock para agregar este producto.");
      return;
    }

    const currentQty = useCartStore.getState().items.find((i) => i.productoId === product.id)?.cantidad ?? 0;
    const result = useCartStore.getState().addToCart(
      product.id,
      product.nombre,
      Number(product.precio_actual || product.precio_base),
      quantity,
      currentQty + effectiveAddable
    );
    if (!result.success) {
      addToast("error", STOCK_EXCEEDED_MESSAGE);
      return;
    }

    useCartStore.getState().setIngredientesExcluidos(product.id, Array.from(excludedIds));
    addToast("exito", `${product.nombre} agregado al carrito`);
    setAdded(true);
    setTimeout(() => setAdded(false), 1200);
  };

  // ── Render ──
  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      {/* Back button */}
      <button
        onClick={() => navigate(-1)}
        className="text-blue-600 hover:text-blue-800 text-sm cursor-pointer"
      >
        &larr; Volver
      </button>

      {/* Image carousel */}
      {product.imagenes_url && product.imagenes_url.length > 0 ? (
        <ImageCarousel
          images={product.imagenes_url}
          publicIds={[]}
          onDelete={() => {}}
          readOnly={true}
          className="max-w-md"
        />
      ) : (
        <div className="w-full aspect-[16/9] bg-gray-300 flex items-center justify-center text-gray-500 rounded">
          Sin imagenes
        </div>
      )}

      {/* Product info */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">{product.nombre}</h1>
        {product.descripcion && (
          <p className="text-gray-600 mt-2">{product.descripcion}</p>
        )}
        {product.receta && isStaff && (
          <div className="mt-3 p-3 bg-gray-50 rounded">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">Receta</h3>
            <p className="text-gray-600 text-sm whitespace-pre-wrap">{product.receta}</p>
          </div>
        )}
        <p className="text-2xl font-bold text-blue-700 mt-3">
          {formatCurrency(product.precio_actual || product.precio_base)}
          {product.unidad_medida_simbolo && (
            <> / {product.unidad_medida_simbolo}</>
          )}
        </p>

        {/* Availability + Stock */}
        {!product.disponible && (
          <span className="inline-block mt-2 text-sm text-red-600 font-medium">
            No disponible
          </span>
        )}
        {product.disponible && currentStock <= 0 && (
          <span className="inline-block mt-2 text-sm text-red-600 font-medium">
            Sin stock
          </span>
        )}
        {product.disponible && currentStock > 0 && (
          <div className="flex items-center gap-2 mt-2">
            <span className="text-sm text-gray-600">
              Stock: {currentStock}
            </span>
            {/* WebSocket connection indicator */}
            {liveStock !== null && (
              <span className="relative flex h-2 w-2">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${wsConnected ? "bg-green-400" : "bg-red-400"}`} />
                <span className={`relative inline-flex rounded-full h-2 w-2 ${wsConnected ? "bg-green-500" : "bg-red-500"}`} />
              </span>
            )}
          </div>
        )}
      </div>

      {/* Ingredient list */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-3">Ingredientes</h2>
        {ingredientsLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-5 bg-gray-200 rounded w-1/2 animate-pulse" />
            ))}
          </div>
        ) : ingredients.length === 0 ? (
          <p className="text-gray-500 text-sm">Este producto no tiene ingredientes registrados.</p>
        ) : (
          <ul className="space-y-2">
            {ingredients.map((ing) => (
              <li key={ing.ingrediente_id} className="flex items-center gap-2 text-gray-700">
                <span>{ing.ingrediente_nombre}</span>
                {ing.es_alergeno && <AllergenBadge />}
                {ing.es_removible && (
                  <span className="text-xs text-gray-400">(removible)</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Add-to-cart section — hidden for admin/stock/guests */}
      {isClientOrPedidos && (
        <div className="border-t pt-4 space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">Agregar al carrito</h2>

          {/* Quantity selector */}
          <div className="flex items-center gap-3">
            <label htmlFor="quantity" className="text-sm font-medium text-gray-700">
              Cantidad:
            </label>
            <DecimalInput
              id="quantity"
              value={quantity}
              onChange={(v) => setQuantity(v)}
              decimals={0}
              min={1}
              max={effectiveAddable}
              step={1}
              disabled={isUnavailable}
              width="min-w-[8ch]"
            />
          </div>

          {/* Removable ingredient checkboxes */}
          {removableIngredients.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">
                Excluir ingredientes:
              </p>
              <div className="space-y-1">
                {removableIngredients.map((ing) => (
                  <label
                    key={ing.ingrediente_id}
                    className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={excludedIds.has(ing.ingrediente_id)}
                      onChange={() => handleToggleExclusion(ing.ingrediente_id)}
                      disabled={isUnavailable}
                      className="rounded"
                    />
                    Sin {ing.ingrediente_nombre}
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Add to cart button */}
          <button
            onClick={handleAddToCart}
            disabled={isUnavailable}
            title={isUnavailable ? (isSharedLimited && limitantes.length > 0 ? `Limitado por ${limitantes.join(", ")} en tu carrito` : unavailableLabel) : undefined}
            className={`px-6 py-2 rounded font-medium text-white transition-colors cursor-pointer ${
              isUnavailable
                ? "bg-gray-400 cursor-not-allowed"
                : added
                  ? "bg-green-600"
                  : "bg-blue-600 hover:bg-blue-700"
            }`}
          >
            {isUnavailable
              ? unavailableLabel
              : added
                ? "OK Agregado"
                : "Agregar al carrito"}
          </button>
        </div>
      )}

      {/* Stock Historial — admin/staff only */}
      {isStaff && (
        <div className="border-t pt-4">
          <h2 className="text-xl font-semibold text-gray-900 mb-3">Historial de Stock</h2>
          {!isNaN(productoId) && (
            <StockHistorialTab entidadTipo="producto" entidadId={productoId} />
          )}
        </div>
      )}
    </div>
  );
}
