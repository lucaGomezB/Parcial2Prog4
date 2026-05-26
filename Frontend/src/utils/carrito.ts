const STORAGE_KEY = "carrito";

export interface CarritoItem {
  productoId: number;
  nombre: string;
  precio: number;
  cantidad: number;
}

export function getCarrito(): CarritoItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as CarritoItem[];
  } catch {
    return [];
  }
}

function guardar(items: CarritoItem[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

export function addToCart(productoId: number, nombre: string, precio: number, cantidad = 1): CarritoItem[] {
  const items = getCarrito();
  const existing = items.find((i) => i.productoId === productoId);
  if (existing) {
    existing.cantidad += cantidad;
  } else {
    items.push({ productoId, nombre, precio, cantidad });
  }
  guardar(items);
  return items;
}

export function removeFromCart(productoId: number): CarritoItem[] {
  const items = getCarrito().filter((i) => i.productoId !== productoId);
  guardar(items);
  return items;
}

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

export function getTotal(): number {
  return getCarrito().reduce((sum, i) => sum + i.precio * i.cantidad, 0);
}

export function getItemCount(): number {
  return getCarrito().reduce((sum, i) => sum + i.cantidad, 0);
}

export function clearCarrito(): void {
  localStorage.removeItem(STORAGE_KEY);
}
