/**
 * ProductCard — Reusable card component for displaying products in a grid view.
 *
 * Features:
 *  - Product image with progressive degradation (API URL -> public/ fallback -> gray square)
 *  - Name, formatted price, availability status
 *  - "Agregar al carrito" button with green flash feedback on add
 *  - Disabled state for unavailable or out-of-stock products
 *
 * State management: simple props-driven; visual feedback via recentlyAdded Set.
 */
import { useState } from "react";
import type { Producto } from "../api/productos";

// ── ProductImage sub-component ──

/**
 * Renders a product image with progressive degradation:
 *  1. imagenes_url[0] (API-provided image)
 *  2. /productos/{id}.jpg (public/ directory fallback)
 *  3. Gray square placeholder on total failure
 *
 * The onError handler advances through sources in order.
 */
function ProductImage({ imagenes_url, id }: { imagenes_url: string[]; id: number }) {
  const sources = imagenes_url[0]
    ? [imagenes_url[0], `/productos/${id}.jpg`]
    : [`/productos/${id}.jpg`];

  const [currentIndex, setCurrentIndex] = useState(0);
  const [allFailed, setAllFailed] = useState(false);

  const handleError = () => {
    const nextIndex = currentIndex + 1;
    if (nextIndex < sources.length) {
      setCurrentIndex(nextIndex);
    } else {
      setAllFailed(true);
    }
  };

  if (allFailed) {
    return (
      <div className="w-full aspect-[4/3] bg-gray-300 flex items-center justify-center text-gray-500">
        Sin imagen
      </div>
    );
  }

  return (
    <img
      src={sources[currentIndex]}
      alt="Producto"
      className="w-full aspect-[4/3] object-cover"
      onError={handleError}
    />
  );
}

// ── Public API ──

interface ProductCardProps {
  product: Producto;
  onAddToCart: (prod: Producto) => void;
  recentlyAdded: Set<number>;
}

export default function ProductCard({ product, onAddToCart, recentlyAdded }: ProductCardProps) {
  const isUnavailable = !product.disponible || product.stock_cantidad <= 0;
  const isRecent = recentlyAdded.has(product.id);

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg flex flex-col">
      {/* Image section */}
      <ProductImage imagenes_url={product.imagenes_url} id={product.id} />

      {/* Content */}
      <div className="p-4 flex flex-col flex-1">
        <h3 className="font-semibold text-lg mb-1">{product.nombre}</h3>
        <p className="text-gray-700 text-sm mb-2">
          ${Number(product.precio_actual).toFixed(2)}
        </p>

        {/* Availability indicator */}
        {!product.disponible && (
          <span className="text-xs text-red-600 font-medium mb-2">No disponible</span>
        )}
        {product.disponible && product.stock_cantidad <= 0 && (
          <span className="text-xs text-red-600 font-medium mb-2">Sin stock</span>
        )}

        {/* Add-to-cart button */}
        <div className="mt-auto">
          {isUnavailable ? (
            <button
              disabled
              className="w-full px-4 py-2 rounded-b-lg font-medium text-white transition-colors cursor-not-allowed disabled:bg-gray-400 disabled:text-gray-600"
            >
              {!product.disponible ? "No disponible" : "Sin stock"}
            </button>
          ) : (
            <button
              onClick={() => onAddToCart(product)}
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
