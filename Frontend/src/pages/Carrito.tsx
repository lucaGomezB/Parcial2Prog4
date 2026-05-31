import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  getCarrito,
  removeFromCart,
  updateCantidad,
  getTotal,
  getItemCount,
  clearCarrito,
  type CarritoItem,
} from "../utils/carrito";
import { AxiosError } from "axios";
import { pedidosApi, type ValidarStockDetalle, type ValidarStockInput } from "../api/pedidos";
import {
  direccionesApi,
  formatDireccion,
  type DireccionEntrega,
  type DireccionEntregaInput,
} from "../api/direcciones";
import { getAccessToken } from "../api/client";
import { useAppForm, required } from "../hooks/useAppForm";

/* ── Modal rápido para crear dirección desde el carrito ── */
function NuevaDireccionModal({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (data: DireccionEntregaInput) => Promise<void>;
}) {
  const [guardando, setGuardando] = useState(false);

  const form = useAppForm({
    defaultValues: { alias: "", linea1: "", linea2: "", ciudad: "" },
    onSubmit: async ({ value }) => {
      setGuardando(true);
      try {
        await onSave({
          alias: value.alias.trim() || null,
          linea1: value.linea1.trim(),
          linea2: value.linea2.trim() || null,
          ciudad: value.ciudad.trim(),
          es_principal: false,
        });
        onClose();
      } finally {
        setGuardando(false);
      }
    },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-4">Nueva Dirección de Entrega</h2>
        <form onSubmit={(e) => { e.preventDefault(); e.stopPropagation(); void form.handleSubmit(); }} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Alias</label>
            <form.Field name="alias">
              {(field) => (
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Ej: Casa, Trabajo..."
                  maxLength={50}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              )}
            </form.Field>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Calle y Número <span className="text-red-500">*</span>
            </label>
            <form.Field name="linea1" validators={{ onChange: required() }}>
              {(field) => (
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Av. Siempre Viva 123"
                  required
                  maxLength={100}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              )}
            </form.Field>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Piso / Dpto</label>
            <form.Field name="linea2">
              {(field) => (
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Piso 3, Dpto B"
                  maxLength={100}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              )}
            </form.Field>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ciudad <span className="text-red-500">*</span>
            </label>
            <form.Field name="ciudad" validators={{ onChange: required() }}>
              {(field) => (
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="Ciudad"
                  required
                  maxLength={100}
                  className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                />
              )}
            </form.Field>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-100 cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={guardando || !form.state.values.linea1.trim() || !form.state.values.ciudad.trim()}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
            >
              {guardando ? "Guardando..." : "Agregar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Modal de advertencia de stock ── */
function StockWarningModal({
  detalles,
  onAdjust,
  onClose,
}: {
  detalles: ValidarStockDetalle[];
  onAdjust: (ajustes: Record<string, number>) => void;
  onClose: () => void;
}) {
  const [ajustes, setAjustes] = useState<Record<string, number>>(() => {
    const init: Record<string, number> = {};
    for (const d of detalles) {
      const key = `${d.producto_id}`;
      init[key] = Math.min(d.cantidad_solicitada, d.stock_disponible);
    }
    return init;
  });

  const handleConfirm = () => {
    onAdjust(ajustes);
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-2xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-1">Stock Insuficiente</h2>
        <p className="text-sm text-gray-600 mb-4">
          Algunos productos no tienen stock suficiente. Ajustá las cantidades o remové los productos para continuar.
        </p>

        <table className="w-full border-collapse border mb-4">
          <thead>
            <tr className="bg-gray-200">
              <th className="border p-2 text-left">Producto</th>
              <th className="border p-2 text-center">Solicitado</th>
              <th className="border p-2 text-center">Stock Disp.</th>
              <th className="border p-2 text-center">Nueva Cant.</th>
              <th className="border p-2 text-center">Acción</th>
            </tr>
          </thead>
          <tbody>
            {detalles.map((d) => {
              const key = `${d.producto_id}`;
              const val = ajustes[key] ?? 0;
              const seraEliminado = val <= 0;
              return (
                <tr key={key} className={seraEliminado ? "bg-red-50" : ""}>
                  <td className="border p-2">{d.nombre_producto}</td>
                  <td className="border p-2 text-center">{d.cantidad_solicitada}</td>
                  <td className="border p-2 text-center font-semibold">{d.stock_disponible}</td>
                  <td className="border p-2 text-center">
                    <input
                      type="number"
                      min={0}
                      max={d.stock_disponible}
                      value={val}
                      onChange={(e) => {
                        const v = Math.min(d.stock_disponible, Math.max(0, Number(e.target.value) || 0));
                        setAjustes((prev) => ({ ...prev, [key]: v }));
                      }}
                      className={`w-20 border rounded px-2 py-1 text-center ${seraEliminado ? "border-red-400 bg-red-100" : "border-gray-300"}`}
                    />
                  </td>
                  <td className="border p-2 text-center">
                    {seraEliminado ? (
                      <span className="text-red-600 text-sm font-medium">Se eliminará</span>
                    ) : (
                      <button
                        onClick={() => setAjustes((prev) => ({ ...prev, [key]: 0 }))}
                        className="bg-red-600 text-white px-2 py-1 rounded text-sm cursor-pointer hover:bg-red-700"
                      >
                        Quitar
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
            onClick={onClose}
            className="px-4 py-2 text-sm border border-gray-300 rounded hover:bg-gray-100 cursor-pointer"
          >
            Cancelar
          </button>
          <button
            onClick={handleConfirm}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 cursor-pointer"
          >
            Confirmar Cambios
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Carrito ── */
export default function Carrito() {
  const navigate = useNavigate();

  // Proteger: solo usuarios autenticados pueden ver el carrito
  useEffect(() => {
    if (!getAccessToken()) {
      navigate("/login", { replace: true });
    }
  }, [navigate]);

  const [items, setItems] = useState<CarritoItem[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [direcciones, setDirecciones] = useState<DireccionEntrega[]>([]);
  const [direccionSelId, setDireccionSelId] = useState<number | "nueva" | null>(null);
  const [showNewDir, setShowNewDir] = useState(false);
  const [loadingDirs, setLoadingDirs] = useState(false);
  const [stockWarnings, setStockWarnings] = useState<ValidarStockDetalle[] | null>(null);

  // Sincronizar estado con localStorage al montar
  useEffect(() => {
    setItems(getCarrito());
  }, []);

  // Forzar re-render cuando vuelven de otra pestaña
  useEffect(() => {
    const onFocus = () => {
      setItems(getCarrito());
      cargarDirecciones();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  // Cargar direcciones al montar
  const cargarDirecciones = async () => {
    setLoadingDirs(true);
    try {
      const data = await direccionesApi.getAll();
      setDirecciones(data);
      // Preseleccionar la principal
      const principal = data.find((d) => d.es_principal);
      if (principal) {
        setDireccionSelId(principal.id);
      } else if (data.length > 0) {
        setDireccionSelId(data[0].id);
      }
    } catch {
      // Si falla la carga de direcciones, no bloquear el carrito
    } finally {
      setLoadingDirs(false);
    }
  };

  useEffect(() => {
    cargarDirecciones();
  }, []);

  const handleRemove = (productoId: number) => {
    setItems(removeFromCart(productoId));
  };

  const handleIncrement = (productoId: number) => {
    const item = items.find((i) => i.productoId === productoId);
    if (item) {
      setItems(updateCantidad(productoId, item.cantidad + 1));
    }
  };

  const handleDecrement = (productoId: number) => {
    const item = items.find((i) => i.productoId === productoId);
    if (item && item.cantidad > 1) {
      setItems(updateCantidad(productoId, item.cantidad - 1));
    }
  };

  const doRealizarPedido = async () => {
    // Leer items frescos de localStorage para evitar stale closure
    const currentItems = getCarrito();
    if (currentItems.length === 0) return;
    setEnviando(true);
    setError(null);

    try {
      // Step 1: Pre-validate stock
      const stockResult = await pedidosApi.validarStock({
        detalles: currentItems.map((i) => ({
          producto_id: i.productoId,
          cantidad: i.cantidad,
        })),
      });

      if (!stockResult.valido) {
        setStockWarnings(stockResult.detalles);
        setEnviando(false);
        return;
      }

      // Step 2: Create the order
      const direccionId = typeof direccionSelId === "number" ? direccionSelId : undefined;
      await pedidosApi.create({
        forma_pago_codigo: "EFECTIVO",
        subtotal: getTotal(),
        descuento: 0,
        costo_envio: direccionId ? 50 : 0,
        direccion_id: direccionId,
        detalles: currentItems.map((i) => ({
          producto_id: i.productoId,
          cantidad: i.cantidad,
          nombre_snapshot: i.nombre,
          precio_snapshot: i.precio,
        })),
      });

      clearCarrito();
      setItems([]);
      navigate("/pedidos");
    } catch (e) {
      // Step 3: Handle 409 from auto-advance (race condition)
      if (e instanceof AxiosError && e.response?.status === 409) {
        const body = e.response.data as Record<string, unknown>;
        // FastAPI wraps detail: { detail: { error: "stock_insuficiente", detalles: [...] } }
        const detail = body?.detail as Record<string, unknown> | undefined;
        if (detail?.error === "stock_insuficiente" && Array.isArray(detail?.detalles)) {
          setStockWarnings(detail.detalles as ValidarStockDetalle[]);
          setEnviando(false);
          return;
        }
      }
      // Generic error handling
      if (e instanceof AxiosError && e.response?.data) {
        const data = e.response.data as Record<string, unknown>;
        const detail = data.detail;
        if (detail != null && typeof detail === "object") {
          setError(JSON.stringify(detail));
        } else if (typeof detail === "string") {
          setError(detail);
        } else if (typeof data.message === "string") {
          setError(data.message);
        } else {
          setError((e as Error).message);
        }
      } else {
        setError((e as Error).message);
      }
    } finally {
      setEnviando(false);
    }
  };

  const handleRealizarPedido = () => {
    doRealizarPedido();
  };

  const handleStockAdjust = (ajustes: Record<string, number>) => {
    for (const [key, nuevaCantidad] of Object.entries(ajustes)) {
      const productoId = Number(key);
      if (nuevaCantidad <= 0) {
        removeFromCart(productoId);
      } else {
        updateCantidad(productoId, nuevaCantidad);
      }
    }
    setStockWarnings(null);
    const freshItems = getCarrito();
    setItems(freshItems);
    // Re-submit with FRESH items (doRealizarPedido reads from getCarrito internamente)
    if (freshItems.length > 0) {
      doRealizarPedido();
    }
  };

  const handleCrearDireccion = async (data: DireccionEntregaInput) => {
    const nueva = await direccionesApi.create(data);
    setDirecciones((prev) => [...prev, nueva]);
    setDireccionSelId(nueva.id);
  };

  const total = getTotal();
  const itemCount = getItemCount();

  if (items.length === 0) {
    return (
      <div className="p-4 text-center">
        <h1 className="text-2xl font-bold mb-4">Carrito</h1>
        <p className="text-gray-500 mb-4">El carrito está vacío</p>
        <Link
          to="/productos"
          className="inline-block bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
        >
          Ver Productos
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Carrito ({itemCount} productos)</h1>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4">
          Error al crear pedido: {error}
        </div>
      )}

      <table className="w-full border-collapse border mb-4">
        <thead>
          <tr className="bg-gray-200">
            <th className="border p-2 text-left">Producto</th>
            <th className="border p-2 text-left">Precio Unitario</th>
            <th className="border p-2 text-center">Cantidad</th>
            <th className="border p-2 text-left">Total</th>
            <th className="border p-2 text-left">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.productoId} className="hover:bg-gray-100 border-b">
              <td className="p-2">{item.nombre}</td>
              <td className="p-2">${Number(item.precio).toFixed(2)}</td>
              <td className="p-2 text-center">
                <span className="inline-flex items-center gap-1">
                  <button
                    onClick={() => handleDecrement(item.productoId)}
                    disabled={item.cantidad <= 1}
                    className="border border-gray-400 bg-white text-gray-700 hover:bg-gray-100 text-sm w-7 h-7 flex items-center justify-center rounded cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    −
                  </button>
                  <span className="w-8 text-center font-mono font-semibold">
                    {item.cantidad}
                  </span>
                  <button
                    onClick={() => handleIncrement(item.productoId)}
                    className="border border-gray-400 bg-white text-gray-700 hover:bg-gray-100 text-sm w-7 h-7 flex items-center justify-center rounded cursor-pointer"
                  >
                    +
                  </button>
                </span>
              </td>
              <td className="p-2 font-mono font-semibold">
                ${(Number(item.precio) * item.cantidad).toFixed(2)}
              </td>
              <td className="p-2">
                <button
                  onClick={() => handleRemove(item.productoId)}
                  className="bg-red-600 text-white px-3 py-1 rounded text-sm cursor-pointer hover:bg-red-700"
                >
                  Quitar
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Selector de dirección de entrega */}
      <div className="border-t pt-4 mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Dirección de entrega</h2>

        {loadingDirs ? (
          <p className="text-sm text-gray-400">Cargando direcciones...</p>
        ) : direcciones.length > 0 ? (
          <div className="flex items-center gap-2">
            <select
              value={direccionSelId ?? ""}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "nueva") {
                  setShowNewDir(true);
                } else {
                  setDireccionSelId(val ? Number(val) : null);
                }
              }}
              className="border border-gray-300 rounded px-3 py-2 text-sm flex-1 max-w-md"
            >
              {direcciones.map((d) => (
                <option key={d.id} value={d.id}>
                  {formatDireccion(d)}{d.es_principal ? " (Principal)" : ""}
                </option>
              ))}
              <option value="nueva" disabled={direcciones.length >= 10}>
                ─ Agregar nueva dirección ─
              </option>
            </select>
            {direccionSelId && typeof direccionSelId === "number" && (
              <span className="text-xs text-green-600 font-medium">
                Con envío (+$50.00)
              </span>
            )}
          </div>
        ) : (
          <button
            onClick={() => setShowNewDir(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 cursor-pointer"
          >
            + Agregar dirección de entrega
          </button>
        )}
      </div>

      <div className="border-t pt-4 flex justify-between items-center">
        <div className="text-xl font-bold">
          Subtotal: <span className="text-blue-700">${total.toFixed(2)}</span>
          {direccionSelId && typeof direccionSelId === "number" && (
            <span className="text-base font-normal text-gray-500 ml-2">
              (+ $50.00 envío)
            </span>
          )}
        </div>
        <button
          onClick={handleRealizarPedido}
          disabled={enviando}
          className="bg-green-700 text-white px-6 py-2 rounded text-lg font-semibold cursor-pointer hover:bg-green-800 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {enviando ? "Creando pedido..." : "Realizar Pedido"}
        </button>
      </div>

      {/* Modal de advertencia de stock */}
      {stockWarnings && (
        <StockWarningModal
          detalles={stockWarnings}
          onAdjust={handleStockAdjust}
          onClose={() => setStockWarnings(null)}
        />
      )}

      {/* Modal nueva dirección */}
      {showNewDir && (
        <NuevaDireccionModal
          onClose={() => setShowNewDir(false)}
          onSave={handleCrearDireccion}
        />
      )}
    </div>
  );
}
