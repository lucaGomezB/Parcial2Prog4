import * as XLSX from "xlsx";

export function exportToExcel<T extends Record<string, unknown>>(
  data: T[],
  filename: string
) {
  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Datos");
  XLSX.writeFile(workbook, `${filename}.xlsx`);
}
