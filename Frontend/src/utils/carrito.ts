import { getUserInfo } from "../api/client";

function storageKey(): string {
  const user = getUserInfo();
  return user?.email ? `carrito_${user.email}` : "carrito";
}

export interface CarritoItem {
  productoId: number;
  nombre: string;
  precio: number;
  cantidad: number;
  medidaId?: number;
  medidaNombre?: string;
}

export function getCarrito(): CarritoItem[] {
  try {
    const raw = localStorage.getItem(storageKey());
    if (!raw) return [];
    return JSON.parse(raw) as CarritoItem[];
  } catch {
    return [];
  }
}

function guardar(items: CarritoItem[]): void {
  localStorage.setItem(storageKey(), JSON.stringify(items));
}

export function addToCart(
  productoId: number,
  nombre: string,
  precio: number,
  cantidad = 1,
  medidaId?: number,
  medidaNombre?: string,
): CarritoItem[] {
  const items = getCarrito();
  const existing = items.find((i) => i.productoId === productoId && i.medidaId === medidaId);
  if (existing) {
    existing.cantidad += cantidad;
  } else {
    items.push({ productoId, nombre, precio: Number(precio), cantidad, medidaId, medidaNombre });
  }
  guardar(items);
  return items;
}

export function removeFromCart(productoId: number, medidaId?: number): CarritoItem[] {
  const items = getCarrito().filter(
    (i) => !(i.productoId === productoId && i.medidaId === medidaId)
  );
  guardar(items);
  return items;
}

export function updateCantidad(productoId: number, cantidad: number, medidaId?: number): CarritoItem[] {
  if (cantidad < 1) return getCarrito();
  const items = getCarrito();
  const item = items.find((i) => i.productoId === productoId && i.medidaId === medidaId);
  if (item) {
    item.cantidad = cantidad;
  }
  guardar(items);
  return items;
}

export function getTotal(): number {
  return getCarrito().reduce((sum, i) => sum + Number(i.precio) * i.cantidad, 0);
}

export function getItemCount(): number {
  return getCarrito().reduce((sum, i) => sum + i.cantidad, 0);
}

export function clearCarrito(): void {
  localStorage.removeItem(storageKey());
}
