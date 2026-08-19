/**
 * ProductCard — Reusable card component for displaying products in a grid view.
 *
 * Features:
 *  - Product image carousel (multiple images with arrow navigation)
 *  - Fallback chain when no product images: category image -> gray placeholder
 *  - Name, formatted price, availability status
 *  - Allergen indicator when product has allergenic ingredients
 *  - Click navigates to /productos/:id (except add-to-cart button)
 *  - "Agregar al carrito" button with green flash feedback on add
 *  - Disabled state for unavailable or out-of-stock products
 *  - In-cart products render a neutral "En carrito" state (not "No disponible")
 *
 * State management: simple props-driven; visual feedback via recentlyAdded Set.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Producto } from "@/features/productos/api/productos";
import { useProductoIngredientes } from "@/features/productos/hooks/useProductos";
import ImageCarousel from "@/shared/components/ImageCarousel";
import AllergenBadge from "@/features/productos/components/AllergenBadge";
import { formatCurrency } from "@/shared/utils/formatCurrency";

// ── Fallback image when product has no own images ──

/**
 * Renders a fallback image when the product has no imagenes_url.
 * Tries: 1) category image, 2) static file, 3) gray placeholder on total failure.
 */
function FallbackImage({ categoryImages, id }: { categoryImages?: string[]; id: number }) {
  const src = categoryImages?.[0] ?? `/productos/${id}.jpg`;
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <div className="w-full aspect-[4/3] bg-gray-300 flex items-center justify-center text-gray-500 rounded">
        Sin imagen
      </div>
    );
  }

  return (
    <img
      src={src}
      alt="Producto"
      className="w-full aspect-[4/3] object-cover rounded-t-lg"
      onError={() => setFailed(true)}
    />
  );
}

// ── Public API ──

interface ProductCardProps {
  product: Producto;
  onAddToCart: (prod: Producto) => void;
  recentlyAdded: Set<number>;
  categoryImages?: string[];
  showId?: boolean;
  /** How many more units can be added given the current cart (0 = unavailable). */
  agregable?: number;
  /** Names of the products in the cart that limit this one (shared ingredient). */
  limitantes?: string[];
  /** Quantity of this product already in the cart (0 = not in cart). */
  enCarrito?: number;
}

export default function ProductCard({ product, onAddToCart, recentlyAdded, categoryImages, showId, agregable, limitantes = [], enCarrito = 0 }: ProductCardProps) {
  const navigate = useNavigate();
  const inCart = enCarrito > 0;
  const effectiveStock = agregable ?? product.stock_cantidad;
  // In-cart products are NOT marked unavailable just because agregable hit 0.
  // Only a catalog-disabled product (disponible === false) remains "No disponible".
  const isUnavailable = !product.disponible || (!inCart && effectiveStock <= 0);
  // Limited by a SHARED ingredient (has own stock but can't be added right now).
  const isSharedLimited = !inCart && product.disponible && product.stock_cantidad > 0 && effectiveStock <= 0;
  // Three distinct states, each with its own clear label:
  //   - "No disponible": catalog flag turned off by the admin (permanent).
  //   - "Limitado por tu carrito": a cart item consumed the shared ingredient.
  //   - "Sin stock": own derived stock is zero (transient, ingredient-based).
  const unavailableLabel = !product.disponible
    ? "No disponible"
    : isSharedLimited
      ? "Limitado por tu carrito"
      : "Sin stock";
  const isRecent = recentlyAdded.has(product.id);

  // Fetch ingredients only when the product has ingredient associations
  const { data: ingredients } = useProductoIngredientes(
    product.tiene_ingredientes ? product.id : 0
  );

  const hasAllergens = product.tiene_ingredientes && ingredients
    ? ingredients.some((ing) => ing.es_alergeno)
    : false;

  const handleCardClick = () => {
    navigate(`/productos/${product.id}`);
  };

  const handleAddToCartClick = (e: React.MouseEvent) => {
    e.stopPropagation(); // prevent card navigation
    onAddToCart(product);
  };

  return (
    <div
      onClick={handleCardClick}
      className="bg-white rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg flex flex-col cursor-pointer"
    >
      {/* Image section — carousel for multiple images, fallback for empty */}
      {product.imagenes_url.length > 0 ? (
        <ImageCarousel
          images={product.imagenes_url}
          publicIds={[]}
          onDelete={() => {}}
          readOnly={true}
        />
      ) : (
        <FallbackImage categoryImages={categoryImages} id={product.id} />
      )}

      {/* Content */}
      <div className="p-4 flex flex-col flex-1">
        <h3 className="font-semibold text-lg mb-1">
          {product.nombre}
          {showId && (
            <span className="ml-2 inline-block px-1.5 py-0.5 rounded text-xs font-mono font-normal bg-gray-100 text-gray-500 align-middle">
              #{product.id}
            </span>
          )}
        </h3>
        <p className="text-gray-700 text-sm mb-2">
          {formatCurrency(product.precio_actual)}
          {product.unidad_medida_simbolo && (
            <> / {product.unidad_medida_simbolo}</>
          )}
        </p>

        {/* Allergen indicator */}
        {hasAllergens && (
          <div className="mb-2">
            <AllergenBadge label="Contiene alergenos" />
          </div>
        )}

        {/* Availability indicator */}
        {isUnavailable && (
          <span
            className="text-xs text-red-600 font-medium mb-2 cursor-help"
            title={isSharedLimited && limitantes.length > 0 ? `Limitado por ${limitantes.join(", ")} en tu carrito` : undefined}
          >
            {unavailableLabel}
          </span>
        )}

        {/* Add-to-cart button */}
        <div className="mt-auto">
          {isUnavailable ? (
            <button
              disabled
              onClick={(e) => e.stopPropagation()}
              className="w-full px-4 py-2 rounded-b-lg font-medium text-white transition-colors cursor-not-allowed disabled:bg-gray-400 disabled:text-gray-600"
            >
              {unavailableLabel}
            </button>
          ) : inCart ? (
            <button
              disabled
              onClick={(e) => e.stopPropagation()}
              className="w-full px-4 py-2 rounded-b-lg font-medium text-white transition-colors cursor-not-allowed bg-green-600"
            >
              En carrito{enCarrito > 1 ? ` (${enCarrito})` : ""}
            </button>
          ) : (
            <button
              onClick={handleAddToCartClick}
              className={`w-full px-4 py-2 rounded-b-lg font-medium text-white transition-colors cursor-pointer ${
                isRecent ? "bg-green-600" : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              {isRecent ? "OK Agregado" : "Agregar al carrito"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
