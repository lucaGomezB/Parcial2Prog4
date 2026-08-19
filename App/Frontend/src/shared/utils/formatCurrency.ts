/**
 * Formats a number or numeric string as Argentine Peso currency.
 *
 * @param value - The number or numeric string to format.
 * @returns A locale-formatted currency string (e.g., "$ 1.234,56").
 */
export function formatCurrency(value: number | string): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "$ 0,00";
  return num.toLocaleString("es-AR", { style: "currency", currency: "ARS" });
}
