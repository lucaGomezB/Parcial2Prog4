/**
 * useDisponibilidadCarrito — returns how many more units of each product can
 * still be added to the cart without exceeding stock, accounting for SHARED
 * ingredients across products (e.g. two products consuming the same cheese).
 *
 * Used by the client menu to proactively mark products as unavailable and to
 * block add-to-cart when a shared ingredient would go negative.
 */
import { useQuery } from '@tanstack/react-query';
import { pedidosApi } from '@/features/pedidos/api/pedidos';
import type { DisponibilidadResponse } from '@/features/pedidos/api/pedidos';

export interface CarritoDisponibilidadItem {
  productoId: number;
  cantidad: number;
}

/**
 * @param productos - product IDs to check availability for (usually the menu).
 * @param carrito - current cart items (productoId + cantidad).
 */
export function useDisponibilidadCarrito(
  productos: number[],
  carrito: CarritoDisponibilidadItem[],
) {
  const cartSignature = carrito
    .map((i) => `${i.productoId}:${i.cantidad}`)
    .sort()
    .join('|');
  const productsSignature = productos.join(',');

  return useQuery<DisponibilidadResponse>({
    queryKey: ['pedidos', 'disponibilidad', productsSignature, cartSignature] as const,
    queryFn: () =>
      pedidosApi.disponibilidad({
        carrito: carrito.map((i) => ({
          producto_id: i.productoId,
          cantidad: i.cantidad,
        })),
        productos,
      }),
    enabled: productos.length > 0,
    staleTime: 0,
    retry: 1,
    // No keepPreviousData: when the cart changes, the query key changes and we
    // want the "agregable" values to reflect the POST-add cart immediately.
    // Showing the previous cart's availability would leave products marked as
    // addable during the refetch window (the exact lag this change fixes). The
    // brief empty-map flash during refetch is the accepted trade-off.
  });
}
