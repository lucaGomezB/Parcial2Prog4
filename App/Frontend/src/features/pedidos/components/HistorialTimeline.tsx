/**
 * HistorialTimeline — Visual timeline of estado transitions for a pedido.
 *
 * Extracted from PedidosPage.tsx. Uses useHistorialPedido() internally.
 * Renders a vertical line with dots, estado transitions, timestamps,
 * and system-flag tags. Estado codes are mapped to user-friendly labels.
 */
import { useHistorialPedido } from '@/features/pedidos/hooks/usePedidos'

const ETIQUETAS_LINEA_TIEMPO: Record<string, string> = {
  PENDIENTE: "Creacion de su pedido",
  CONFIRMADO: "Pedido confirmado",
  EN_PREP: "En preparacion",
  ENTREGADO: "Pedido entregado",
  CANCELADO: "Pedido cancelado",
};

function etiqueta(codigo: string | null | undefined): string {
  if (!codigo) return "";
  return ETIQUETAS_LINEA_TIEMPO[codigo] ?? codigo;
}

interface HistorialTimelineProps {
  pedidoId: number
}

export function HistorialTimeline({ pedidoId }: HistorialTimelineProps) {
  const { data: historial, isLoading } = useHistorialPedido(pedidoId)

  if (isLoading) return <p className="text-xs text-gray-400 mt-3">Cargando historial...</p>
  if (!historial || historial.length === 0) return <p className="text-xs text-gray-400 mt-3">Sin historial de estados</p>

  return (
    <div className="mt-4 border-t pt-3">
      <h3 className="text-md font-semibold mb-3">Linea de tiempo</h3>
      <div className="relative ml-2">
        {historial.map((entry, i) => (
          <div key={entry.id} className="flex gap-3 mb-3 relative">
            <div className="flex flex-col items-center">
              <div className={`w-3 h-3 rounded-full border-2 ${entry.es_sistema ? 'border-gray-300 bg-gray-200' : 'border-blue-500 bg-blue-400'} z-10`} />
              {i < historial.length - 1 && <div className="w-0.5 flex-1 bg-gray-300" />}
            </div>
            <div className="flex-1 pb-1">
              <p className="text-sm">
                {entry.estado_desde ? (
                  <span>
                    <span className="text-gray-500">{etiqueta(entry.estado_desde)}</span>
                    <span className="mx-1 text-gray-400">→</span>
                  </span>
                ) : (
                  <span className="text-gray-400">Creacion </span>
                )}
                <span className="font-medium">{etiqueta(entry.estado_hacia)}</span>
                {entry.es_sistema && <span className="text-xs text-gray-400 ml-1">(sistema)</span>}
              </p>
              {entry.motivo && <p className="text-xs text-red-500 mt-0.5">Motivo: {entry.motivo}</p>}
              <p className="text-xs text-gray-400 mt-0.5">
                {new Date(entry.created_at).toLocaleString("es-AR", {
                  day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
                })}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
