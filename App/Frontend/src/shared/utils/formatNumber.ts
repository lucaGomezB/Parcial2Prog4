/**
 * Formats a number with Argentine locale conventions.
 *
 * Uses "." as thousands separator and "," as decimal separator,
 * with a configurable number of decimal places.
 *
 * @param value  The number to format.
 * @param decimals  Number of decimal places (default 2).
 * @returns A locale-formatted number string (e.g., "1.000,500" for 1000.5 with 3 decimals).
 */
export function formatNumber(value: number, decimals: number = 2): string {
  return value.toLocaleString("es-AR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
