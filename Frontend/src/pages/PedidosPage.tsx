import { useEffect, useState, useCallback } from "react";
import { pedidosApi, type Pedido, type DetallePedido, type StockInsuficienteDetalle } from "../api/pedidos";
import { getUserRoles } from "../api/client";
import { AxiosError } from "axios";

const ESTADOS_COLORES: Record<string, string> = {
  PENDIENTE: "bg-yellow-100 text-yellow-800",
  CONFIRMADO: "bg-blue-100 text-blue-800",
  EN_PREP: "bg-indigo-100 text-indigo-800",
  EN_CAMINO: "bg-purple-100 text-purple-800",
  ENTREGADO: "bg-green-100 text-green-800",
  CANCELADO: "bg-red-100 text-red-800",
};

const ETIQUETAS_AVANCE: Record<string, string> = {
  PENDIENTE: "Confirmar",
  CONFIRMADO: "Preparar",
  EN_PREP: "Enviar",
  EN_CAMINO: "Entregar",
};

const ETIQUETAS_ESTADO: Record<string, string> = {
  PENDIENTE: "Pendiente",
  CONFIRMADO: "Confirmado",
  EN_PREP: "En Preparación",
  EN_CAMINO: "En Camino",
  ENTREGADO: "Entregado",
  CANCELADO: "Cancelado",
};

/* ── Popup de Detalles ── */
function DetallesPopup({ pedido, detalles, onClose }: {
  pedido: Pedido; detalles: DetallePedido[]; onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-2xl max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">Detalles del Pedido #{pedido.id}</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer">✕</button>
        </div>
        <p className="text-sm text-gray-500 mb-3">
          Fecha: {new Date(pedido.created_at).toLocaleString("es-AR")}
        </p>
        <table className="w-full border-collapse border mb-4">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Producto</th>
            <th className="border p-2 text-left">Medida</th>
            <th className="border p-2 text-right">Cantidad</th>
            <th className="border p-2 text-right">Precio Unit.</th>
            <th className="border p-2 text-right">Subtotal</th>
          </tr></thead>
          <tbody>
            {detalles.map((d, i) => (
              <tr key={i} className="hover:bg-gray-100 border-b">
                <td className="p-2">{d.nombre_snapshot}</td>
                <td className="p-2 text-sm">{d.medida_snapshot ?? "-"}</td>
                <td className="p-2 text-right">{d.cantidad}</td>
                <td className="p-2 text-right">${parseFloat(d.precio_snapshot).toFixed(2)}</td>
                <td className="p-2 text-right font-mono font-semibold">${parseFloat(d.subtotal_snap).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="text-right text-lg font-bold">
          Total: <span className="text-blue-700">${parseFloat(pedido.total).toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Popup de resolución de stock insuficiente ── */
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
      <div className="bg-white rounded p-6 w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-amber-800">Stock Insuficiente</h2>
          <button onClick={onCancel} className="text-gray-500 text-xl cursor-pointer">✕</button>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          El pedido <strong>#{pedido.id}</strong> tiene productos con stock insuficiente.
          Ajustá las cantidades o marcá para eliminar los que no tengan stock.
        </p>

        <table className="w-full border-collapse border mb-4">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">Producto</th>
            <th className="border p-2 text-left">Medida</th>
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
                  <td className="p-2 text-sm">{d.medida ?? "-"}</td>
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
                        >−</button>
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

/* ── Página principal ── */
type ModoVista = "activos" | "historial";

export default function PedidosPage() {
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailPopup, setDetailPopup] = useState<Pedido | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);
  const [modo, setModo] = useState<ModoVista>("activos");
  const [stockIssue, setStockIssue] = useState<{ pedido: Pedido; detalles: StockInsuficienteDetalle[] } | null>(null);

  const roles = getUserRoles();
  const esGestor = roles.includes("ADMIN") || roles.includes("PEDIDOS");
  const esHistorial = modo === "historial";

  const loadPedidos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = esHistorial
        ? (esGestor
            ? await pedidosApi.getHistorial()
            : await pedidosApi.getHistorial())
        : (esGestor
            ? await pedidosApi.getActivos()
            : await pedidosApi.getMisPedidos());
      setPedidos(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [esGestor, esHistorial]);

  useEffect(() => { loadPedidos(); }, [loadPedidos]);

  const cambiarModo = (nuevo: ModoVista) => {
    if (nuevo !== modo) setModo(nuevo);
  };

  const handleAvanzar = async (id: number) => {
    try {
      const res = await pedidosApi.avanzar(id);
      setMensaje(res.mensaje);
      loadPedidos();
      setTimeout(() => setMensaje(null), 3000);
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
      setMensaje(res.mensaje);
      loadPedidos();
      setTimeout(() => setMensaje(null), 3000);
    } catch (e) {
      setError((e as Error).message);
      setTimeout(() => setError(null), 3000);
    }
  };

  const handleCancelar = async (id: number) => {
    if (!confirm("¿Estás seguro de cancelar este pedido?")) return;
    try {
      await pedidosApi.cancelar(id);
      setMensaje("Pedido cancelado");
      loadPedidos();
      setTimeout(() => setMensaje(null), 3000);
    } catch (e) {
      setError((e as Error).message);
      setTimeout(() => setError(null), 3000);
    }
  };

  return (
    <div className="p-4">
      {/* Tabs */}
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

      <h1 className="text-2xl font-bold mb-4">
        {esHistorial
          ? "Historial de Pedidos"
          : esGestor
            ? "Gestión de Pedidos"
            : "Mis Pedidos"}
      </h1>

      {mensaje && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-2 rounded mb-4">
          {mensaje}
        </div>
      )}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-gray-500">Cargando pedidos...</p>
      ) : pedidos.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          {esHistorial ? (
            <>
              <p className="text-lg mb-2">No hay historial de pedidos</p>
              <p className="text-sm">Los pedidos entregados o cancelados aparecerán aquí.</p>
            </>
          ) : (
            <>
              <p className="text-lg mb-2">No hay pedidos activos</p>
              <p className="text-sm">Los pedidos finalizados o cancelados no se muestran aquí.</p>
            </>
          )}
        </div>
      ) : (
        <table className="w-full border-collapse border">
          <thead><tr className="bg-gray-200">
            <th className="border p-2 text-left">ID</th>
            {esGestor && <th className="border p-2 text-left">Usuario</th>}
            <th className="border p-2 text-left">Fecha</th>
            <th className="border p-2 text-left">Estado</th>
            <th className="border p-2 text-right">Total</th>
            <th className="border p-2 text-left">Acciones</th>
          </tr></thead>
          <tbody>
            {pedidos.map((ped) => (
              <tr key={ped.id} className="hover:bg-gray-100 border-b">
                <td className="p-2 font-mono">#{ped.id}</td>
                {esGestor && (
                  <td className="p-2">
                    {ped.usuario ? ped.usuario.email : `ID ${ped.usuario_id}`}
                  </td>
                )}
                <td className="p-2 text-sm">
                  {new Date(ped.created_at).toLocaleDateString("es-AR", {
                    day: "2-digit", month: "2-digit", year: "numeric",
                    hour: "2-digit", minute: "2-digit",
                  })}
                </td>
                <td className="p-2">
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${ESTADOS_COLORES[ped.estado_codigo] || "bg-gray-100"}`}>
                    {ETIQUETAS_ESTADO[ped.estado_codigo] || ped.estado_codigo}
                  </span>
                </td>
                <td className="p-2 text-right font-mono font-semibold">
                  ${parseFloat(ped.total).toFixed(2)}
                </td>
                <td className="p-2">
                  <div className="flex gap-1 flex-wrap">
                    <button
                      onClick={() => setDetailPopup(ped)}
                      className="bg-gray-600 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-gray-700"
                    >
                      Ver Detalles
                    </button>
                    {!esHistorial && esGestor && ETIQUETAS_AVANCE[ped.estado_codigo] && (
                      <button
                        onClick={() => handleAvanzar(ped.id)}
                        className="bg-blue-600 text-white px-2 py-1 rounded text-xs cursor-pointer hover:bg-blue-700"
                      >
                        {ETIQUETAS_AVANCE[ped.estado_codigo]}
                      </button>
                    )}
                    {!esHistorial && (
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
      )}

      {/* Popup de detalles */}
      {detailPopup && (
        <DetallesPopup
          pedido={detailPopup}
          detalles={detailPopup.detalles ?? []}
          onClose={() => setDetailPopup(null)}
        />
      )}

      {/* Popup de resolución de stock */}
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
