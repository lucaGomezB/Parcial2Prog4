/**
 * PedidoDetallePage — Full order detail view for a single pedido.
 *
 * Route: /pedidos/:id
 * Access: Client (and admin/pedidos roles via their own route blocks)
 *
 * Displays: order ID, date, status, items list (name, qty, unit price, subtotal),
 * subtotal, shipping, total, payment method.
 */
import { useParams, Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { pedidosApi, type Pedido, type DetallePedido } from "@/features/pedidos/api/pedidos";
import { useEstadoPedidoWS } from "@/features/pedidos/hooks/useEstadoPedidoWS";
import { formatCurrency } from "@/shared/utils/formatCurrency";

const ESTADOS_COLORES: Record<string, string> = {
  PENDIENTE: "bg-yellow-100 text-yellow-800",
  CONFIRMADO: "bg-blue-100 text-blue-800",
  EN_PREP: "bg-indigo-100 text-indigo-800",
  ENTREGADO: "bg-green-100 text-green-800",
  CANCELADO: "bg-red-100 text-red-800",
};

const ETIQUETAS_ESTADO: Record<string, string> = {
  PENDIENTE: "Pendiente",
  CONFIRMADO: "Confirmado",
  EN_PREP: "En Preparacion",
  ENTREGADO: "Entregado",
  CANCELADO: "Cancelado",
};

function formaPagoLabel(codigo: string): string {
  const labels: Record<string, string> = {
    MERCADOPAGO: "MercadoPago",
    PAGO_LOCAL: "Pago y retiro en local",
    TRANSFERENCIA: "Transferencia",
  };
  return labels[codigo] || codigo;
}

/** Full-page skeleton shown while the query is loading. */
function DetalleSkeleton() {
  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-3xl mx-auto bg-white rounded-lg shadow p-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-48 mb-4" />
        <div className="h-4 bg-gray-200 rounded w-32 mb-6" />
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-full" />
          <div className="h-4 bg-gray-200 rounded w-3/4" />
        </div>
        <div className="mt-6 h-4 bg-gray-200 rounded w-40" />
      </div>
    </div>
  );
}

/** Error state when the pedido cannot be found. */
function PedidoNotFound({ id }: { id: string }) {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="max-w-md mx-auto bg-white rounded-lg shadow p-8 text-center">
        <h2 className="text-xl font-bold text-gray-800 mb-2">Pedido no encontrado</h2>
        <p className="text-gray-600 mb-6">
          El pedido #{id} no existe o no tienes permisos para verlo.
        </p>
        <Link
          to="/pedidos"
          className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Volver a mis pedidos
        </Link>
      </div>
    </div>
  );
}

/** Renders the list of order items. */
function ItemsTable({ detalles }: { detalles: DetallePedido[] }) {
  return (
    <table className="w-full border-collapse border rounded-lg overflow-hidden">
      <thead>
        <tr className="bg-gray-100">
          <th className="border p-3 text-left text-sm font-semibold text-gray-700">Producto</th>
          <th className="border p-3 text-center text-sm font-semibold text-gray-700">Cantidad</th>
          <th className="border p-3 text-right text-sm font-semibold text-gray-700">Precio Unit.</th>
          <th className="border p-3 text-right text-sm font-semibold text-gray-700">Subtotal</th>
        </tr>
      </thead>
      <tbody>
        {detalles.map((d, i) => (
          <tr key={i} className="border-b hover:bg-gray-50 transition-colors">
            <td className="p-3 text-gray-800">{d.nombre_snapshot}</td>
            <td className="p-3 text-center text-gray-600">{d.cantidad}</td>
            <td className="p-3 text-right font-mono text-gray-800">{formatCurrency(d.precio_snapshot)}</td>
            <td className="p-3 text-right font-mono font-semibold text-gray-900">
              {formatCurrency(d.subtotal_snap)}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Renders the pricing summary (subtotal, shipping, total). */
function ResumenPrecios({ pedido }: { pedido: Pedido }) {
  return (
    <div className="bg-gray-50 rounded-lg p-4 space-y-2">
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">Subtotal</span>
        <span className="font-mono">{formatCurrency(pedido.subtotal)}</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">Envio</span>
        <span className="font-mono">{formatCurrency(pedido.costo_envio)}</span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-gray-600">Descuento</span>
        <span className="font-mono">{formatCurrency(pedido.descuento)}</span>
      </div>
      <div className="flex justify-between text-lg font-bold border-t pt-2 mt-2">
        <span>Total</span>
        <span className="text-blue-700">{formatCurrency(pedido.total)}</span>
      </div>
    </div>
  );
}

export default function PedidoDetallePage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const pedidoId = Number(id);

  // Real-time updates: subscribe to this pedido's WebSocket channel and
  // refresh the query whenever a state-change event arrives (e.g. an admin
  // advances the order, or it is cancelled).
  useEstadoPedidoWS(pedidoId, !!id && !Number.isNaN(pedidoId), () => {
    queryClient.invalidateQueries({ queryKey: ["pedido", id] });
  });

  const {
    data: pedido,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["pedido", id],
    queryFn: () => pedidosApi.getById(Number(id)),
    enabled: !!id,
    retry: 3,
    retryDelay: 1000,
  });

  if (isLoading) return <DetalleSkeleton />;

  if (isError || !pedido) {
    // Axios errors: 404/403 = not found or forbidden
    const axiosError = error as { response?: { status?: number } } | null;
    const status = axiosError?.response?.status;
    if (status === 404 || status === 403 || !pedido) {
      return <PedidoNotFound id={id ?? "?"} />;
    }
    // Unexpected error
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <div className="max-w-md mx-auto bg-white rounded-lg shadow p-8 text-center">
          <h2 className="text-xl font-bold text-red-700 mb-2">Error</h2>
          <p className="text-gray-600 mb-6">
            No se pudo cargar el pedido. Intenta nuevamente.
          </p>
          <Link
            to="/pedidos"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Volver a mis pedidos
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-3xl mx-auto">
        {/* ── Back link ── */}
        <Link
          to="/pedidos"
          className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 mb-4 transition-colors"
        >
          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Volver a mis pedidos
        </Link>

        {/* ── Main card ── */}
        <div className="bg-white rounded-lg shadow">
          {/* Header */}
          <div className="p-6 border-b">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <h1 className="text-2xl font-bold text-gray-900">
                Pedido #{pedido.id}
              </h1>
              <span
                className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                  ESTADOS_COLORES[pedido.estado_codigo] || "bg-gray-100 text-gray-800"
                }`}
              >
                {ETIQUETAS_ESTADO[pedido.estado_codigo] || pedido.estado_codigo}
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-2">
              {new Date(pedido.created_at).toLocaleDateString("es-AR", {
                year: "numeric",
                month: "long",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>

            {/* Meta info row */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Metodo de pago:</span>{" "}
                <span className="font-medium">{formaPagoLabel(pedido.forma_pago_codigo)}</span>
              </div>
              <div>
                {pedido.direccion_id ? (
                  <span className="text-blue-600">Envio a domicilio</span>
                ) : (
                  <span className="text-green-600">Retiro en el local</span>
                )}
              </div>
              {pedido.notas && (
                <div className="sm:col-span-2">
                  <span className="text-gray-500">Notas:</span>{" "}
                  <span className="text-gray-700">{pedido.notas}</span>
                </div>
              )}
            </div>
          </div>

          {/* Items */}
          {pedido.detalles && pedido.detalles.length > 0 && (
            <div className="p-6 border-b">
              <h2 className="text-lg font-semibold text-gray-800 mb-3">Productos</h2>
              <ItemsTable detalles={pedido.detalles} />
            </div>
          )}

          {/* Pricing summary */}
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Resumen</h2>
            <ResumenPrecios pedido={pedido} />
          </div>
        </div>
      </div>
    </div>
  );
}
