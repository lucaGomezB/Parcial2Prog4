/**
 * StockHistorialTab — displays the audit trail for product/ingredient stock changes.
 *
 * Fetches GET /api/v1/stock/historial/{entidad_tipo}/{entidad_id} and renders
 * a color-coded timeline table showing stock mutations over time.
 *
 * Only visible to ADMIN/STOCK roles.
 */
import { useQuery } from "@tanstack/react-query";
import { getHistorial, type HistorialStockEntry } from "@/features/productos/api/stockHistorial";

// ── Motivo color mapping ──
const MOTIVO_COLORS: Record<string, string> = {
  creacion: "bg-green-100 text-green-800",
  actualizacion: "bg-blue-100 text-blue-800",
  venta: "bg-red-100 text-red-800",
  cancelacion: "bg-orange-100 text-orange-800",
  soft_delete: "bg-gray-100 text-gray-800",
  reconciliacion: "bg-purple-100 text-purple-800",
};

const MOTIVO_LABELS: Record<string, string> = {
  creacion: "Creacion",
  actualizacion: "Actualizacion",
  venta: "Venta",
  cancelacion: "Cancelacion",
  soft_delete: "Eliminacion",
  reconciliacion: "Reconciliacion",
};

interface StockHistorialTabProps {
  entidadTipo: "producto" | "ingrediente";
  entidadId: number;
}

export default function StockHistorialTab({ entidadTipo, entidadId }: StockHistorialTabProps) {
  const {
    data,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["stock-historial", entidadTipo, entidadId],
    queryFn: () => getHistorial(entidadTipo, entidadId),
    enabled: !!entidadId,
  });

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-2 p-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-6 bg-gray-200 rounded w-full" />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-gray-500 p-4">
        No se pudo cargar el historial de stock.
      </p>
    );
  }

  if (data.items.length === 0) {
    return (
      <p className="text-sm text-gray-500 p-4">
        No hay cambios de stock registrados.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-gray-500">
            <th className="p-2 font-medium">Fecha</th>
            <th className="p-2 font-medium">Stock Anterior</th>
            <th className="p-2 font-medium">Stock Nuevo</th>
            <th className="p-2 font-medium">Diferencia</th>
            <th className="p-2 font-medium">Motivo</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((entry: HistorialStockEntry) => {
            const diff = entry.stock_nuevo - entry.stock_anterior;
            const diffSign = diff > 0 ? "+" : "";
            return (
              <tr key={entry.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="p-2 text-gray-600">
                  {new Date(entry.created_at).toLocaleString('es-AR')}
                </td>
                <td className="p-2">{entry.stock_anterior}</td>
                <td className="p-2">{entry.stock_nuevo}</td>
                <td className={`p-2 ${diff > 0 ? "text-green-600" : diff < 0 ? "text-red-600" : "text-gray-500"}`}>
                  {diffSign}{diff}
                </td>
                <td className="p-2">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${MOTIVO_COLORS[entry.motivo] || "bg-gray-100 text-gray-800"}`}>
                    {MOTIVO_LABELS[entry.motivo] || entry.motivo}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
