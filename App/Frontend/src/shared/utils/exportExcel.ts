/**
 * Excel export utility.
 *
 * Wraps the xlsx library (SheetJS) to provide a simple function that converts
 * an array of objects into an .xlsx file and triggers a browser download.
 *
 * No styling or complex formatting is applied — the output is a plain table
 * where each object key becomes a column header and each value becomes a cell.
 *
 * Usage:
 *   exportToExcel(products, "productos-reporte");
 *   // → downloads "productos-reporte.xlsx"
 */
import * as XLSX from "xlsx";

/**
 * Exports an array of records as an .xlsx file.
 *
 * @typeParam T - Record type whose keys become column headers.
 * @param data  - Array of objects to export. All objects should share the same keys.
 * @param filename - Output filename (without extension — ".xlsx" is appended automatically).
 */
export function exportToExcel<T extends Record<string, unknown>>(
  data: T[],
  filename: string
) {
  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Datos");
  XLSX.writeFile(workbook, `${filename}.xlsx`);
}
