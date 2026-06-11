/**
 * PedidosPage — Orders listing and management page.
 *
 * Features:
 *   - Dual view: "activos" (in-progress) vs "historial" (completed/cancelled).
 *   - Role-based rendering:
 *       - ADMIN/PEDIDOS (gestor): sees all orders with state-advance buttons.
 *       - CLIENT: sees only their last 10 active orders, no advance buttons.
 *   - Order state FSM: PENDIENTE -> CONFIRMADO -> EN_PREP -> EN_CAMINO -> ENTREGADO
 *   - State badges with color coding via ESTADOS_COLORES.
 *   - Detail modal (DetallesPopup) for viewing order line items.
 *   - Stock resolution modal (StockModal) for handling stock_insuficiente errors.
 *   - Cancel action (with restrictions based on role and state).
 *   - Auto-limitation: clients see at most 10 active orders (with a banner).
 *
 * Sub-components:
 *   - DetallesPopup: modal showing order line items (product, qty, price, subtotal).
 *   - StockModal: modal for adjusting quantities when stock is insufficient.
 */

import { useEffect, useState, useCallback } from "react";
import { pedidosApi, type Pedido, type DetallePedido, type StockInsuficienteDetalle } from "../api/pedidos";
import { pagosApi, type PagoRead } from "../api/pagos";
import { getUserRoles } from "../api/client";
import { AxiosError } from "axios";

/**
 * FSM state colors for order status badges.
 * Keys match the backend's estado_codigo values.
 */
const ESTADOS_COLORES: Record<string, string> = {
  PENDIENTE: "bg-yellow-100 text-yellow-800",
  CONFIRMADO: "bg-blue-100 text-blue-800",
  EN_PREP: "bg-indigo-100 text-indigo-800",
  EN_CAMINO: "bg-purple-100 text-purple-800",
  ENTREGADO: "bg-green-100 text-green-800",
  CANCELADO: "bg-red-100 text-red-800",
};

/**
 * Maps non-terminal states to the label text for the "advance" action button.
 * Terminal states (ENTREGADO, CANCELADO) have no entry here.
 */
const ETIQUETAS_AVANCE: Record<string, string> = {
  PENDIENTE: "Confirmar",
  CONFIRMADO: "Preparar",
  EN_PREP: "Enviar",
  EN_CAMINO: "Entregar",
};

/** Human-readable labels for each order state. */
const ETIQUETAS_ESTADO: Record<string, string> = {
  PENDIENTE: "Pendiente",
  CONFIRMADO: "Confirmado",
  EN_PREP: "En Preparacion",
  EN_CAMINO: "En Camino",
  ENTREGADO: "Entregado",
  CANCELADO: "Cancelado",
};

/**
 * DetallesPopup — Modal showing the line items (detalles) of a single order.
 *
 * Props:
 *   - pedido: the order (used for ID, date, total).
 *   - detalles: array of line items (product snapshot, qty, price, subtotal).
 *   - onClose: callback to close the modal.
 *   - esGestor: if true, prepends the order ID to the title.
 *
 * Snapshot fields (nombre_snapshot, precio_snapshot, subtotal_snap):
 * These are a copy of the product name/price at the time the order was placed.
 * If prices change later, existing orders still show the original agreed prices.
 */
/**
 * Returns a human-readable label for a MercadoPago payment status.
 */
function mpStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "Pendiente",
    approved: "Aprobado",
    rejected: "Rechazado",
    refunded: "Reintegrado",
    cancelled: "Cancelado",
    in_process: "En proceso",
    in_mediation: "En mediacion",
    charged_back: "Contracargo",
  };
  return labels[status] || status;
}

/**
 * Color classes for MercadoPago payment status badges.
 */
const MP_STATUS_COLORS: Record<string, string> = {
  pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  refunded: "bg-purple-100 text-purple-800",
  cancelled: "bg-gray-100 text-gray-800",
  in_process: "bg-blue-100 text-blue-800",
};

function DetallesPopup({ pedido, detalles, onClose, esGestor, pagos }: {
  pedido: Pedido; detalles: DetallePedido[]; onClose: () => void; esGestor?: boolean; pagos?: PagoRead[];
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-2xl max-h-[80vh]" style={{ overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Detalles del Pedido{esGestor ? ` #${pedido.id}` : ""}</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">X</button>
        </div>
        <p className="text-sm text-gray-500 mb-1">
          Fecha: {new Date(pedido.created_at).toLocaleString("es-AR")}
        </p>
        <p className="text-sm mb-3">
          {pedido.direccion_id ? (
            <span className="text-blue-600">Envio a domicilio</span>
          ) : (
            <span className="text-green-600">Retiro en el local</span>
          )}
        </p>
        <p className="text-sm mb-3">
          <span className="font-medium">Metodo de pago:</span>{" "}
          {pedido.forma_pago_codigo === "MERCADOPAGO" ? "MercadoPago" : "Efectivo"}
        </p>
        <table className="w-full border-collapse border mb-4">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Producto</th>
            <th className="border p-2 text-right">Cantidad</th>
            <th className="border p-2 text-right">Precio Unit.</th>
            <th className="border p-2 text-right">Subtotal</th>
          </tr></thead>
          <tbody>
            {detalles.map((d, i) => (
              <tr key={i} className="hover:bg-gray-100 border-b">
                <td className="p-2">{d.nombre_snapshot}</td>
                <td className="p-2 text-right">{d.cantidad}</td>
                <td className="p-2 text-right">${parseFloat(d.precio_snapshot).toFixed(2)}</td>
                <td className="p-2 text-right font-mono font-semibold">${parseFloat(d.subtotal_snap).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="text-right text-lg font-bold mb-4">
          Total: <span className="text-blue-700">${parseFloat(pedido.total).toFixed(2)}</span>
        </div>

        {/* Payment status section — only for gestor users */}
        {esGestor && pagos && pagos.length > 0 && (
          <>
            <h3 className="text-md font-semibold mb-2 border-t pt-3">Pagos</h3>
            <table className="w-full border-collapse border">
              <thead><tr className="bg-gray-100">
                <th className="border p-2 text-left">Estado</th>
                <th className="border p-2 text-right">Monto</th>
                <th className="border p-2 text-left">Detalle</th>
                <th className="border p-2 text-left">Metodo</th>
                <th className="border p-2 text-left">Fecha</th>
              </tr></thead>
              <tbody>
                {pagos.map((p) => (
                  <tr key={p.id} className="border-b hover:bg-gray-50">
                    <td className="p-2">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${MP_STATUS_COLORS[p.mp_status] || "bg-gray-100"}`}>
                        {mpStatusLabel(p.mp_status)}
                      </span>
                    </td>
                    <td className="p-2 text-right font-mono">${p.transaction_amount.toFixed(2)}</td>
                    <td className="p-2 text-xs text-gray-600">{p.mp_status_detail || "-"}</td>
                    <td className="p-2 text-xs">{p.payment_method_id || "-"}</td>
                    <td className="p-2 text-xs">
                      {new Date(p.created_at).toLocaleDateString("es-AR", {
                        day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * StockModal — Modal for resolving stock_insuficiente errors.
 *
 * When a manager confirms an order but there isn't enough stock, the backend
 * responds with 409 Conflict + details. This modal lets the manager:
 *   - Reduce quantities per product (within available stock).
 *   - Mark products for removal (quantity = 0).
 *   - Confirm to apply changes and re-attempt order advancement.
 *
 * Initial quantities are set to the available stock via useState initializer.
 */
function StockModal({ pedido, detalles, onResolve, onCancel }: {
  pedido: Pedido;
  detalles: StockInsuficienteDetalle[];
  onResolve: (resoluciones: Record<number, number>) => Promise<void>;
  onCancel: () => void;
}) {
  const [resoluciones, setResoluciones] = useState<Record<number, number>>(() => {
    const init: Record<number, number> = {};
    for (const d of detalles) {
      init[d.producto_id] = d.stock_disponible;
    }
    return init;
  });
  const [resolving, setResolving] = useState(false);

  const handleConfirmar = async () => {
    setResolving(true);
    try {
      await onResolve(resoluciones);
    } finally {
      setResolving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onCancel}>
      <div className="bg-white rounded p-6 w-full max-w-lg" style={{ overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-amber-800">Stock Insuficiente</h2>
          <button onClick={onCancel} className="text-gray-500 text-xl cursor-pointer">X</button>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          El pedido <strong>#{pedido.id}</strong> tiene productos con stock insuficiente.
          Ajusta las cantidades o marca para eliminar los que no tengan stock.
        </p>

        <table className="w-full border-collapse border mb-4">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Producto</th>
            <th className="border p-2 text-right">Pedido</th>
            <th className="border p-2 text-right">Stock</th>
            <th className="border p-2 text-right">Cantidad</th>
          </tr></thead>
          <tbody>
            {detalles.map((d) => {
              const cant = resoluciones[d.producto_id] ?? 0;
              const eliminar = cant <= 0;
              return (
                <tr key={d.producto_id} className={`border-b ${eliminar ? 'bg-red-50 opacity-60' : ''}`}>
                  <td className="p-2">{d.nombre_producto}</td>
                  <td className="p-2 text-right text-red-600">{d.cantidad_solicitada}</td>
                  <td className="p-2 text-right text-green-700">{d.stock_disponible}</td>
                  <td className="p-2 text-right">
                    {eliminar ? (
                      <span className="text-xs text-red-500 font-medium">Eliminado</span>
                    ) : (
                      <div className="inline-flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => setResoluciones((prev) => {
                            const next = { ...prev, [d.producto_id]: Math.max(0, (prev[d.producto_id] ?? d.stock_disponible) - 1) };
                            return next;
                          })}
                          disabled={cant <= 1}
                          className="border border-gray-400 bg-white text-gray-700 hover:bg-gray-100 text-sm w-6 h-6 flex items-center justify-center rounded cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                        >-</button>
                        <span className="w-6 text-center font-mono text-sm">{cant}</span>
                        <button
                          type="button"
                          onClick={() => setResoluciones((prev) => ({ ...prev, [d.producto_id]: Math.min(d.stock_disponible, (prev[d.producto_id] ?? d.stock_disponible) + 1) }))}
                          disabled={cant >= d.stock_disponible}
                          className="border border-gray-400 bg-white text-gray-700 hover:bg-gray-100 text-sm w-6 h-6 flex items-center justify-center rounded cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                        >+</button>
                      </div>
                    )}
                  </td>
                  <td className="p-2 text-center">
                    {d.stock_disponible === 0 ? (
                      <span className="text-xs text-gray-400">Sin stock</span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setResoluciones((prev) => {
                          if ((prev[d.producto_id] ?? d.stock_disponible) > 0) {
                            return { ...prev, [d.producto_id]: 0 };
                          }
                          return { ...prev, [d.producto_id]: d.stock_disponible };
                        })}
                        className={`text-xs px-2 py-0.5 rounded cursor-pointer ${eliminar ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' : 'bg-red-100 text-red-700 hover:bg-red-200'}`}
                      >
                        {eliminar ? "Restaurar" : "Eliminar"}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={resolving}
            className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-100 cursor-pointer disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleConfirmar}
            disabled={resolving}
            className="px-4 py-2 text-sm bg-amber-600 text-white rounded hover:bg-amber-700 cursor-pointer disabled:opacity-50"
          >
            {resolving ? "Aplicando..." : "Aplicar cambios y confirmar"}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * PedidosPage — Main component.
 *
 * View modes (ModoVista):
 *   - "activos": non-terminal orders (PENDIENTE, CONFIRMADO, EN_PREP, EN_CAMINO).
 *   - "historial": terminal orders (ENTREGADO, CANCELADO).
 *
 * Role behavior:
 *   - Gestor (ADMIN/PEDIDOS): sees all orders, can advance/cancel states.
 *   - Client: sees only last 10 active orders, no advance button.
 *
 * Render states:
 *   1. Loading -> spinner text.
 *   2. Error -> red banner (auto-clears after 3s).
 *   3. Empty -> descriptive empty state per view mode.
 *   4. Data -> full table with action buttons.
 *   5. Popups -> DetallesPopup and StockModal (overlaid).
 */
type ModoVista = "activos" | "historial";

export default function PedidosPage() {
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailPopup, setDetailPopup] = useState<Pedido | null>(null);
  const [pagosMap, setPagosMap] = useState<Record<number, PagoRead[]>>({});
  const [mensaje, setMensaje] = useState<{tipo: 'exito' | 'error'; texto: string} | null>(null);
  const [modo, setModo] = useState<ModoVista>("activos");
  const [stockIssue, setStockIssue] = useState<{ pedido: Pedido; detalles: StockInsuficienteDetalle[] } | null>(null);

  const roles = getUserRoles();
  const esGestor = roles.includes("ADMIN") || roles.includes("PEDIDOS");
  const esHistorial = modo === "historial";

  const [limiteExcedido, setLimiteExcedido] = useState(false);

  /** Helper to show a timed toast message. */
  const mostrarMensaje = (tipo: 'exito' | 'error', texto: string) => {
    setMensaje({ tipo, texto });
    setTimeout(() => setMensaje(null), 3000);
  };

  /**
   * Fetches orders from the backend.
   * - "activos": calls pedidosApi.getActivos().
   * - "historial": calls pedidosApi.getHistorial().
   *
   * Client filter: non-gestor, non-historial views show max 10 active orders.
   * If there are more than 10, a banner is shown (limiteExcedido).
   */
  const loadPedidos = useCallback(async () => {
    setLoading(true);
    setError(null);
    setLimiteExcedido(false);
    try {
      const data = esHistorial
        ? await pedidosApi.getHistorial()
        : await pedidosApi.getActivos();

      // Clients: only last 10 active orders
      const finalData = esGestor || esHistorial ? data : data.slice(0, 10);
      if (!esGestor && !esHistorial && data.length > 10) {
        setLimiteExcedido(true);
      }

      setPedidos(finalData);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [esGestor, esHistorial]);

  useEffect(() => { loadPedidos(); }, [loadPedidos]);

  /** Switches between "activos" and "historial" view modes. */
  const cambiarModo = (nuevo: ModoVista) => {
    if (nuevo !== modo) setModo(nuevo);
  };

  /**
   * Advances an order to its next FSM state.
   * Calls pedidosApi.avanzar(id) on the backend.
   *
   * Error 409 (Conflict) handling:
   * If the response body has detail.error === "stock_insuficiente",
   * the StockModal is shown instead of displaying a generic error.
   */
  const handleAvanzar = async (id: number) => {
    try {
      const res = await pedidosApi.avanzar(id);
      mostrarMensaje('exito', res.mensaje);
      loadPedidos();
    } catch (e) {
      if (e instanceof AxiosError && e.response?.status === 409 && e.response.data) {
        const body = e.response.data as { detail?: { error: string; mensaje: string; detalles: StockInsuficienteDetalle[] } };
        if (body.detail?.error === "stock_insuficiente") {
          const pedido = pedidos.find(p => p.id === id);
          if (pedido) {
            setStockIssue({ pedido, detalles: body.detail.detalles });
            return;
          }
        }
      }
      setError((e as Error).message);
      setTimeout(() => setError(null), 3000);
    }
  };

  /**
   * Applies stock adjustments from StockModal and re-attempts order advancement.
   * For each product, calls pedidosApi.actualizarDetalle() with the adjusted qty.
   * Quantity = 0 means the product line is removed from the order.
   */
  const handleResolverStock = async (resoluciones: Record<number, number>) => {
    if (!stockIssue) return;
    try {
      // Apply each resolution
      for (const [productoIdStr, cantidad] of Object.entries(resoluciones)) {
        const productoId = Number(productoIdStr);
        await pedidosApi.actualizarDetalle(stockIssue.pedido.id, productoId, cantidad);
      }
      // Retry confirmation
      const res = await pedidosApi.avanzar(stockIssue.pedido.id);
      setStockIssue(null);
      mostrarMensaje('exito', res.mensaje);
      loadPedidos();
    } catch (e) {
      setError((e as Error).message);
      setTimeout(() => setError(null), 3000);
    }
  };

  /**
   * Cancels an order.
   * Uses the native browser confirm() dialog before proceeding.
   *
   * Restrictions:
   *   - Clients cannot cancel orders that are in EN_PREP state
   *     (the button is hidden via conditional render).
   */
  const handleCancelar = async (id: number) => {
    if (!confirm("Estas seguro de cancelar este pedido?")) return;
    try {
      await pedidosApi.cancelar(id);
      mostrarMensaje('exito', 'Pedido cancelado correctamente');
      loadPedidos();
    } catch (e) {
      setError((e as Error).message);
      setTimeout(() => setError(null), 3000);
    }
  };

  return (
    <div className="p-4">
      {/* Tab bar: Activos | Historial */}
      <div className="flex gap-1 mb-4 border-b border-gray-300">
        <button
          onClick={() => cambiarModo("activos")}
          className={`px-4 py-2 text-sm font-medium rounded-t cursor-pointer transition-colors ${
            modo === "activos"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Activos
        </button>
        <button
          onClick={() => cambiarModo("historial")}
          className={`px-4 py-2 text-sm font-medium rounded-t cursor-pointer transition-colors ${
            modo === "historial"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}
        >
          Historial
        </button>
      </div>

      {/* Dynamic title based on mode and role */}
      <h1 className="text-2xl font-bold mb-4">
        {esHistorial
          ? "Historial de Pedidos"
          : esGestor
            ? "Gestion de Pedidos"
            : "Mis Pedidos"}
      </h1>

      {/* Feedback banners */}
      {mensaje && (
        <div className={`p-3 mb-4 rounded ${mensaje.tipo === 'exito' ? 'bg-green-100 text-green-800 border border-green-400' : 'bg-red-100 text-red-800 border border-red-400'}`}>
          {mensaje.texto}
        </div>
      )}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}

      {/* Content area: loading / empty / table */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Cargando pedidos...</span>
          </div>
      ) : pedidos.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          {esHistorial ? (
            <>
              <p className="text-lg mb-2">No hay historial de pedidos</p>
              <p className="text-sm">Los pedidos entregados o cancelados apareceran aqui.</p>
            </>
          ) : (
            <>
              <p className="text-lg mb-2">No hay pedidos activos</p>
              <p className="text-sm">Los pedidos finalizados o cancelados no se muestran aqui.</p>
            </>
          )}
        </div>
      ) : (
        <>
          {/* Limit banner for clients (more than 10 active orders) */}
          {limiteExcedido && (
            <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-2 rounded mb-4 text-sm">
              Mostrando los ultimos 10 pedidos activos. Los anteriores estan disponibles en el historial.
            </div>
          )}

          {/* Orders table — columns adapt based on role */}
          <table className="w-full border-collapse border">
            <thead><tr className="bg-gray-200">
              {esGestor && <th className="border p-2 text-left">Pedido #</th>}
              {esGestor && <th className="border p-2 text-left">Usuario</th>}
              <th className="border p-2 text-left">Fecha</th>
              <th className="border p-2 text-left">Estado</th>
              <th className="border p-2 text-left">Entrega</th>
              <th className="border p-2 text-right">Total</th>
              <th className="border p-2 text-left">Acciones</th>
            </tr></thead>
            <tbody>
              {pedidos.map((ped) => (
                <tr key={ped.id} className={`hover:bg-gray-100 border-b ${ped.deleted_at ? 'bg-red-50' : ''}`}>
                  {esGestor && <td className="p-2 font-mono">#{ped.id}</td>}
                  {esGestor && (
                    <td className="p-2">
                      {ped.usuario ? ped.usuario.email : `Usuario #${ped.usuario_id}`}
                    </td>
                  )}
                  <td className="p-2 text-sm">
                    {new Date(ped.created_at).toLocaleDateString("es-AR", {
                      day: "2-digit", month: "2-digit", year: "numeric",
                      hour: "2-digit", minute: "2-digit",
                    })}
                  </td>
                  {/* State badge with role-specific color */}
                  <td className="p-2">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${ESTADOS_COLORES[ped.estado_codigo] || "bg-gray-100"}`}>
                      {ETIQUETAS_ESTADO[ped.estado_codigo] || "Estado desconocido"}
                    </span>
                  </td>
                  <td className="p-2 text-xs">
                    {ped.direccion_id ? (
                      <span className="text-blue-600 font-medium">Envio</span>
                    ) : (
                      <span className="text-green-600 font-medium">Retiro en local</span>
                    )}
                  </td>
                  <td className="p-2 text-right font-mono font-semibold">
                    ${parseFloat(ped.total).toFixed(2)}
                  </td>
                  <td className="p-2">
                    <div className="flex gap-1 flex-wrap">
                      <button
                        onClick={async () => {
                          setDetailPopup(ped);
                          if (esGestor && !pagosMap[ped.id]) {
                            try {
                              const pagos = await pagosApi.getPagosByPedido(ped.id);
                              setPagosMap((prev) => ({ ...prev, [ped.id]: pagos }));
                            } catch {
                              // Payment data is optional — silently ignore errors
                            }
                          }
                        }}
                        className="bg-gray-600 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-gray-700"
                      >
                        Ver Detalles
                      </button>
                      {/* Advance button: only for gestor, non-terminal states */}
                      {!esHistorial && esGestor && ETIQUETAS_AVANCE[ped.estado_codigo] && (
                        <button
                          onClick={() => handleAvanzar(ped.id)}
                          className="bg-blue-600 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-blue-700"
                        >
                          {ETIQUETAS_AVANCE[ped.estado_codigo]}
                        </button>
                      )}
                      {/* Cancel button: gestor always, client only if not EN_PREP */}
                      {!esHistorial && (esGestor || ped.estado_codigo !== "EN_PREP") && (
                        <button
                          onClick={() => handleCancelar(ped.id)}
                          className="bg-red-600 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-red-700"
                        >
                          Cancelar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* Detail popup modal */}
      {detailPopup && (
        <DetallesPopup
          pedido={detailPopup}
          detalles={detailPopup.detalles ?? []}
          onClose={() => setDetailPopup(null)}
          esGestor={esGestor}
          pagos={pagosMap[detailPopup.id]}
        />
      )}

      {/* Stock resolution modal */}
      {stockIssue && (
        <StockModal
          pedido={stockIssue.pedido}
          detalles={stockIssue.detalles}
          onResolve={handleResolverStock}
          onCancel={() => setStockIssue(null)}
        />
      )}
    </div>
  );
}
