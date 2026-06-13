/**
 * Shopping cart Zustand store with localStorage persistence.
 *
 * The cart is persisted to localStorage with email-scoped keys
 * (carrito_{email}) so that each authenticated user has their own cart,
 * and guests share a "carrito" key.
 *
 * On auth change (login/logout), the store re-hydrates from the new key.
 */
import { create } from 'zustand';
import { getUserInfo } from '../api/client';

// ── Types ──

export interface CarritoItem {
  productoId: number;
  nombre: string;
  precio: number;
  cantidad: number;
  ingredientesExcluidos: number[];
}

interface CartState {
  items: CarritoItem[];
}

interface CartActions {
  /** Hydrate the store from localStorage using the current user's key. */
  hydrate: () => void;
  /** Add a product to the cart, or increment quantity if already present. */
  addToCart: (productoId: number, nombre: string, precio: number, cantidad?: number) => void;
  /** Remove a product from the cart entirely. */
  removeFromCart: (productoId: number) => void;
  /** Set the exact quantity for a product (ignores < 1). */
  updateCantidad: (productoId: number, cantidad: number) => void;
  /** Set the excluded ingredient IDs for a specific product. */
  setIngredientesExcluidos: (productoId: number, ids: number[]) => void;
  /** Empty the cart entirely. */
  clearCarrito: () => void;
  /** Total price of all items. */
  getTotal: () => number;
  /** Total count of individual items (sum of quantities). */
  getItemCount: () => number;
}

type CartStore = CartState & CartActions;

// ── Storage helpers (email-scoped keys) ──

function storageKey(): string {
  const user = getUserInfo();
  return user?.email ? `carrito_${user.email}` : 'carrito';
}

function readFromLS(): CarritoItem[] {
  try {
    const raw = localStorage.getItem(storageKey());
    if (!raw) return [];
    return JSON.parse(raw) as CarritoItem[];
  } catch {
    return [];
  }
}

function writeToLS(items: CarritoItem[]): void {
  localStorage.setItem(storageKey(), JSON.stringify(items));
}

// ── Store ──

export const useCartStore = create<CartStore>((set, get) => ({
  items: readFromLS(),

  hydrate: () => {
    set({ items: readFromLS() });
  },

  addToCart: (productoId, nombre, precio, cantidad = 1) => {
    const items = get().items;
    const existing = items.find((i) => i.productoId === productoId);
    let newItems: CarritoItem[];

    if (existing) {
      newItems = items.map((i) =>
        i.productoId === productoId
          ? { ...i, cantidad: i.cantidad + cantidad }
          : i
      );
    } else {
      newItems = [...items, { productoId, nombre, precio: Number(precio), cantidad, ingredientesExcluidos: [] }];
    }

    writeToLS(newItems);
    set({ items: newItems });
  },

  removeFromCart: (productoId) => {
    const newItems = get().items.filter((i) => i.productoId !== productoId);
    writeToLS(newItems);
    set({ items: newItems });
  },

  updateCantidad: (productoId, cantidad) => {
    if (cantidad < 1) return;
    const newItems = get().items.map((i) =>
      i.productoId === productoId ? { ...i, cantidad } : i
    );
    writeToLS(newItems);
    set({ items: newItems });
  },

  setIngredientesExcluidos: (productoId, ids) => {
    const newItems = get().items.map((i) =>
      i.productoId === productoId ? { ...i, ingredientesExcluidos: ids } : i
    );
    writeToLS(newItems);
    set({ items: newItems });
  },

  clearCarrito: () => {
    localStorage.removeItem(storageKey());
    set({ items: [] });
  },

  getTotal: () => {
    return get().items.reduce((sum, i) => sum + Number(i.precio) * i.cantidad, 0);
  },

  getItemCount: () => {
    return get().items.reduce((sum, i) => sum + i.cantidad, 0);
  },
}));

// ── Selectors ──

export const useCartItems = () => useCartStore((s) => s.items);
export const useCartTotal = () => useCartStore((s) => s.getTotal());
export const useCartCount = () => useCartStore((s) => s.getItemCount());
