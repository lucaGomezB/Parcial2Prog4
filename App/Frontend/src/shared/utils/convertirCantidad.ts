/**
 * Converts a quantity from one unit to another using conversion factors.
 * Matches the backend _convertir_cantidad() logic exactly.
 *
 * @param cantidad - The quantity to convert
 * @param unidadOrigenId - The source unit ID (may be null)
 * @param unidadDestinoId - The target unit ID (may be null)
 * @param factores - Map of unit ID to conversion factor
 * @returns The converted quantity, or cantidad unchanged if conversion cannot be applied
 */
export function convertirCantidad(
  cantidad: number,
  unidadOrigenId: number | null,
  unidadDestinoId: number | null,
  factores: Record<number, number>,
): number {
  if (unidadOrigenId === null || unidadDestinoId === null) return cantidad;
  if (unidadOrigenId === unidadDestinoId) return cantidad;
  const factorOrigen = factores[unidadOrigenId] ?? 1;
  const factorDestino = factores[unidadDestinoId] ?? 1;
  return cantidad * (factorOrigen / factorDestino);
}
