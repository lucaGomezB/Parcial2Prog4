/**
 * Stock Historial API — fetches the audit trail for product/ingredient stock changes.
 */
import { apiFetch } from "@/shared/api/client";

export interface HistorialStockEntry {
  id: number;
  entidad_tipo: string;
  entidad_id: number;
  stock_anterior: number;
  stock_nuevo: number;
  motivo: string;
  usuario_id: number | null;
  created_at: string;
}

export async function getHistorial(
  entidad_tipo: string,
  entidad_id: number,
  skip: number = 0,
  limit: number = 100,
): Promise<{ items: HistorialStockEntry[]; total: number; skip: number; limit: number }> {
  return apiFetch(
    `/stock/historial/${entidad_tipo}/${entidad_id}?skip=${skip}&limit=${limit}`
  );
}
