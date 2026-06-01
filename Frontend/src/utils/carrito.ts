/**
 * Shopping cart utilities.
 *
 * The cart is persisted in localStorage so that items survive page refreshes.
 * Each authenticated user gets their own cart keyed by email ("carrito_{email}"),
 * while unauthenticated (guest) users share a common "carrito" key.
 *
 * When the user logs out or logs in as a different user, the cart switches
 * to the new user's key automatically because `storageKey()` reads the
 * current user info from the auth store at each call.
 *
 * All mutation functions return the updated item array so that callers can
 * reactively update their local state if needed.
 */
import { getUserInfo } from "../api/client";

// ── Storage key ──

/**
 * Returns the localStorage key for the current user.
 * Scoped by email so that different users have independent carts.
 * Falls back to a shared "carrito" key for guests.
 */
function storageKey(): string {
  const user = getUserInfo();
  return user?.email ? `carrito_${user.email}` : "carrito";
}

// ── Types ──

export interface CarritoItem {
  productoId: number;
  nombre: string;
  precio: number;
  cantidad: number;
}

// ── Internal helpers ──

/**
 * Reads the cart from localStorage.
 * Returns an empty array if the key does not exist or JSON parsing fails
 * (e.g., corrupted data).
 */
export function getCarrito(): CarritoItem[] {
  try {
    const raw = localStorage.getItem(storageKey());
    if (!raw) return [];
    return JSON.parse(raw) as CarritoItem[];
  } catch {
    // Corrupted localStorage data — silently return empty cart.
    return [];
  }
}

/**
 * Writes the full cart array to localStorage under the current user's key.
 */
function guardar(items: CarritoItem[]): void {
  localStorage.setItem(storageKey(), JSON.stringify(items));
}

// ── Public API ──

/**
 * Adds a product to the cart, or increments its quantity if it already exists.
 * @returns The updated cart items array.
 */
export function addToCart(
  productoId: number,
  nombre: string,
  precio: number,
  cantidad = 1,
): CarritoItem[] {
  const items = getCarrito();
  const existing = items.find((i) => i.productoId === productoId);
  if (existing) {
    // Product already in cart — increase quantity instead of duplicating.
    existing.cantidad += cantidad;
  } else {
    items.push({ productoId, nombre, precio: Number(precio), cantidad });
  }
  guardar(items);
  return items;
}

/**
 * Removes a product from the cart entirely.
 * @returns The updated cart items array.
 */
export function removeFromCart(productoId: number): CarritoItem[] {
  const items = getCarrito().filter(
    (i) => i.productoId !== productoId
  );
  guardar(items);
  return items;
}

/**
 * Sets the exact quantity for a product in the cart.
 * Ignores quantities below 1 (does not remove — use removeFromCart for that).
 * @returns The updated cart items array.
 */
export function updateCantidad(productoId: number, cantidad: number): CarritoItem[] {
  if (cantidad < 1) return getCarrito();
  const items = getCarrito();
  const item = items.find((i) => i.productoId === productoId);
  if (item) {
    item.cantidad = cantidad;
  }
  guardar(items);
  return items;
}

/**
 * Calculates the total price of all items in the cart.
 * Uses `Number()` conversion to handle string-encoded prices from the API.
 */
export function getTotal(): number {
  return getCarrito().reduce((sum, i) => sum + Number(i.precio) * i.cantidad, 0);
}

/**
 * Returns the total number of individual items in the cart (sum of quantities).
 */
export function getItemCount(): number {
  return getCarrito().reduce((sum, i) => sum + i.cantidad, 0);
}

/**
 * Empties the cart entirely by removing the current user's localStorage key.
 */
export function clearCarrito(): void {
  localStorage.removeItem(storageKey());
}
