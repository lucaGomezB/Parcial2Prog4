/**
 * Carrito — Shopping cart page.
 *
 * Access: authenticated users only (redirects to /login if no token).
 *
 * Features:
 *   - Display all cart items from localStorage (via getCarrito()).
 *   - Increment/decrement quantity per item.
 *   - Remove items from cart.
 *   - Select delivery address (or pickup at the store).
 *   - Create a new address inline via a quick modal.
 *   - Pre-validate stock before creating the order.
 *   - Stock conflict resolution modal when stock is insufficient.
 *   - Order creation flow: validate -> create -> redirect to /pedidos.
 *   - Empty cart state with a link back to the product listing.
 *
 * Cart data is persisted in localStorage (see store/cartStore).
 * Direcciones are fetched from the API and cached in local state.
 */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCartStore, type CarritoItem } from "../store/cartStore";
import { AxiosError } from "axios";
import { pedidosApi, type ValidarStockDetalle, type ValidarStockInput } from "../api/pedidos";
import { productosApi, type ProductoIngredienteRead } from "../api/productos";
import {
  direccionesApi,
  formatDireccion,
  type DireccionEntrega,
  type DireccionEntregaInput,
} from "../api/direcciones";
import { pagosApi } from "../api/pagos";
import { getAccessToken } from "../api/client";
import { useAppForm, required } from "../hooks/useAppForm";

/* ── Modal rapido para crear direccion desde el carrito ── */

/**
 * Modal for quickly creating a new delivery address inline (from the cart page).
 *
 * Fields: alias (optional), linea1 (required), linea2 (optional), ciudad (required).
 * The address is saved to the API, added to the local list, and auto-selected.
 */
function NuevaDireccionModal({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (data: DireccionEntregaInput) => Promise<void>;
}) {
  const [guardando, setGuardando] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const form = useAppForm({
    defaultValues: { alias: "", linea1: "", linea2: "", ciudad: "" },
    onSubmit: async ({ value }) => {
      setGuardando(true);
      setModalError(null);
      try {
        await onSave({
          alias: value.alias.trim() || null,
          linea1: value.linea1.trim(),
          linea2: value.linea2.trim() || null,
          ciudad: value.ciudad.trim(),
          es_principal: false,
        });
        onClose();
      } catch {
        setModalError("Error al guardar la direccion. Intente nuevamente.");
        setTimeout(() => setModalError(null), 4000);
      } finally {
        setGuardando(false);
      }
    },
  });

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-md" style={{ overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-4">Nueva Direccion de Entrega</h2>
        {modalError && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4 text-sm">
            {modalError}
          </div>
        )}
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
              Calle y Numero <span className="text-red-500">*</span>
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

/**
 * Modal shown when stock validation fails before order creation.
 *
 * The user can adjust quantities (within available stock) or remove items entirely.
 * On confirm, the adjustments are applied to the cart and the order is re-attempted.
 *
 * Initial quantities are clamped to min(cantidad_solicitada, stock_disponible).
 */
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
      <div className="bg-white rounded p-6 w-full max-w-2xl" style={{ overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-1">Stock Insuficiente</h2>
        <p className="text-sm text-gray-600 mb-4">
          Algunos productos no tienen stock suficiente. Ajusta las cantidades o elimina los productos para continuar.
        </p>

        <table className="w-full border-collapse border mb-4">
          <thead>
            <tr className="bg-gray-200">
              <th className="border p-2 text-left">Producto</th>
              <th className="border p-2 text-center">Solicitado</th>
              <th className="border p-2 text-center">Stock disponible</th>
              <th className="border p-2 text-center">Nueva Cant.</th>
              <th className="border p-2 text-center">Accion</th>
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
                      <span className="text-red-600 text-sm font-medium">Se eliminara</span>
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

/**
 * Carrito — Main shopping cart component.
 *
 * Cart items are read from localStorage and sync'd on mount and focus events.
 * The checkout flow follows these steps:
 *   1. Pre-validate stock via pedidosApi.validarStock().
 *   2. If stock OK -> create the order via pedidosApi.create().
 *   3. If stock fails -> show StockWarningModal, adjust, re-attempt.
 *   4. On 409 from create (race condition) -> parse stock_insuficiente error.
 *   5. On success -> clear cart, navigate to /pedidos.
 */
export default function Carrito() {
  const navigate = useNavigate();

  // Guard: only authenticated users can access the cart
  useEffect(() => {
    if (!getAccessToken()) {
      navigate("/login", { replace: true });
    }
  }, [navigate]);

  const items = useCartStore((s) => s.items);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [direcciones, setDirecciones] = useState<DireccionEntrega[]>([]);
  const [direccionSelId, setDireccionSelId] = useState<number | "nueva" | null>(null);
  const [showNewDir, setShowNewDir] = useState(false);
  const [loadingDirs, setLoadingDirs] = useState(false);
  const [stockWarnings, setStockWarnings] = useState<ValidarStockDetalle[] | null>(null);
  const [mensaje, setMensaje] = useState<{ tipo: 'exito' | 'error'; texto: string } | null>(null);
  const [formaPago, setFormaPago] = useState<string>("EFECTIVO");
  const [mpCheckoutUrl, setMpCheckoutUrl] = useState<string | null>(null);
  const [ingredientesPorProducto, setIngredientesPorProducto] = useState<Record<number, ProductoIngredienteRead[]>>({});

  /**
   * Re-hydrates cart from localStorage on window focus.
   * This handles cases where the user modifies the cart in another tab
   * or comes back after navigating away.
   */
  useEffect(() => {
    const onFocus = () => {
      useCartStore.getState().hydrate();
      cargarDirecciones();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  /** Fetches all saved addresses, auto-selecting the primary one if available. */
  const cargarDirecciones = async () => {
    setLoadingDirs(true);
    try {
      const data = await direccionesApi.getAll();
      setDirecciones(data);
      // If there are addresses, pre-select the primary one (or the first)
      // If no addresses exist, direccionSelId stays null = "Retirar en el local"
      if (data.length > 0) {
        const principal = data.find((d) => d.es_principal);
        setDireccionSelId(principal ? principal.id : data[0].id);
      }
    } catch {
      // If address loading fails, don't block the cart UI
    } finally {
      setLoadingDirs(false);
    }
  };

  useEffect(() => {
    cargarDirecciones();
  }, []);

  /** Load removable ingredients for each product in the cart. */
  useEffect(() => {
    const items = useCartStore.getState().items;
    const ids = [...new Set(items.map(i => i.productoId))];

    Promise.all(
      ids.map(async (id) => {
        try {
          const ingredientes = await productosApi.getIngredientes(id);
          return { id, ingredientes: ingredientes.filter(i => i.es_removible) };
        } catch {
          return { id, ingredientes: [] };
        }
      })
    ).then((results) => {
      const map: Record<number, ProductoIngredienteRead[]> = {};
      results.forEach(r => { map[r.id] = r.ingredientes; });
      setIngredientesPorProducto(map);
    });
  }, []);

  /** Removes an item from the cart entirely. */
  const handleRemove = (productoId: number) => {
    useCartStore.getState().removeFromCart(productoId);
  };

  /** Increments quantity for a cart item. */
  const handleIncrement = (productoId: number) => {
    const item = items.find((i) => i.productoId === productoId);
    if (item) {
      useCartStore.getState().updateCantidad(productoId, item.cantidad + 1);
    }
  };

  /** Decrements quantity for a cart item (minimum 1). */
  const handleDecrement = (productoId: number) => {
    const item = items.find((i) => i.productoId === productoId);
    if (item && item.cantidad > 1) {
      useCartStore.getState().updateCantidad(productoId, item.cantidad - 1);
    }
  };

  /**
   * Core checkout logic.
   *
   * 1. Validates stock via the backend.
   * 2. If stock is valid, creates the order.
   * 3. If stock is insufficient, shows the StockWarningModal.
   * 4. Handles 409 Conflict errors (race condition on stock).
   */
  const doRealizarPedido = async () => {
    // Read fresh items from Zustand store to avoid stale closure
    const currentItems = useCartStore.getState().items;
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
      const pedido = await pedidosApi.create({
        forma_pago_codigo: formaPago,
        subtotal: useCartStore.getState().getTotal(),
        descuento: 0,
        costo_envio: direccionId ? 50 : 0,
        direccion_id: direccionId,
        detalles: currentItems.map((i) => ({
          producto_id: i.productoId,
          cantidad: i.cantidad,
          nombre_snapshot: i.nombre,
          precio_snapshot: i.precio,
          ...(i.ingredientesExcluidos.length > 0 ? { personalizacion: i.ingredientesExcluidos } : {}),
        })),
      });

      useCartStore.getState().clearCarrito();

      // Step 3: If MERCADOPAGO, initiate payment and show checkout URL
      if (formaPago === "MERCADOPAGO") {
        try {
          const paymentResult = await pagosApi.initPayment(pedido.id);
          setMpCheckoutUrl(paymentResult.init_point);
          setMensaje({ tipo: 'exito', texto: 'Pedido creado. Haga clic en el boton de pago para continuar.' });
        } catch {
          setMensaje({ tipo: 'exito', texto: 'Pedido creado correctamente. Complete el pago desde la seccion de pedidos.' });
          setTimeout(() => navigate("/pedidos"), 2000);
        }
      } else {
        setMensaje({ tipo: 'exito', texto: 'Pedido creado correctamente' });
        setTimeout(() => navigate("/pedidos"), 1500);
      }
    } catch (e) {
      // Step 3: Handle 409 from auto-advance (stock race condition)
      if (e instanceof AxiosError && e.response?.status === 409) {
        const body = e.response.data as Record<string, unknown>;
        // FastAPI wraps detail in { detail: { error: "stock_insuficiente", detalles: [...] } }
        const detail = body?.detail as Record<string, unknown> | undefined;
        if (detail?.error === "stock_insuficiente" && Array.isArray(detail?.detalles)) {
          setStockWarnings(detail.detalles as ValidarStockDetalle[]);
          setEnviando(false);
          return;
        }
      }
      // Generic error handling — extract detail or message
      if (e instanceof AxiosError && e.response?.data) {
        const data = e.response.data as Record<string, unknown>;
        const detail = data.detail;
        if (typeof detail === 'string') {
          setError(detail);
        } else if (typeof detail === 'object') {
          const obj = detail as Record<string, unknown>;
          if (obj.mensaje && typeof obj.mensaje === 'string') {
            setError(obj.mensaje);
          } else if (obj.detalles && Array.isArray(obj.detalles)) {
            setError('No hay stock suficiente para completar el pedido.');
          } else {
            setError('Error al procesar el pedido. Verifique los datos.');
          }
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

  /**
   * After stock adjustments from StockWarningModal:
   * 1. Apply adjustments to localStorage (remove or update quantities).
   * 2. Re-submit the order with the adjusted items.
   */
  const handleStockAdjust = (ajustes: Record<string, number>) => {
    for (const [key, nuevaCantidad] of Object.entries(ajustes)) {
      const productoId = Number(key);
      if (nuevaCantidad <= 0) {
        useCartStore.getState().removeFromCart(productoId);
      } else {
        useCartStore.getState().updateCantidad(productoId, nuevaCantidad);
      }
    }
    setStockWarnings(null);
    const freshItems = useCartStore.getState().items;
    // Re-submit with fresh items (doRealizarPedido reads from the store internally)
    if (freshItems.length > 0) {
      doRealizarPedido();
    }
  };

  /** Creates a new address, adds it to the list, and selects it. */
  const handleCrearDireccion = async (data: DireccionEntregaInput) => {
    const nueva = await direccionesApi.create(data);
    setDirecciones((prev) => [...prev, nueva]);
    setDireccionSelId(nueva.id);
  };

  const total = useCartStore((s) => s.getTotal());
  const itemCount = useCartStore((s) => s.getItemCount());

  // Empty cart state
  if (items.length === 0) {
    return (
      <div className="p-4 text-center">
        <h1 className="text-2xl font-bold mb-4">Carrito</h1>
        <p className="text-gray-500 mb-4">El carrito esta vacio</p>
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

      {/* Success/Error banner */}
      {mensaje && (
        <div className={`p-3 mb-4 rounded border ${mensaje.tipo === 'exito' ? 'bg-green-100 text-green-800 border-green-400' : 'bg-red-100 text-red-800 border-red-400'}`}>
          {mensaje.texto}
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4">
          Error al crear pedido: {error}
        </div>
      )}

      {/* Cart items table */}
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
              <td className="p-2">
                <div>{item.nombre}</div>
                {ingredientesPorProducto[item.productoId]?.length > 0 && (
                  <div className="mt-1 space-y-1">
                    {ingredientesPorProducto[item.productoId].map((ing) => (
                      <label key={ing.ingrediente_id} className="flex items-center gap-1 text-xs text-gray-600">
                        <input
                          type="checkbox"
                          checked={!item.ingredientesExcluidos.includes(ing.ingrediente_id)}
                          onChange={() => {
                            const excluidos = item.ingredientesExcluidos.includes(ing.ingrediente_id)
                              ? item.ingredientesExcluidos.filter(id => id !== ing.ingrediente_id)
                              : [...item.ingredientesExcluidos, ing.ingrediente_id];
                            useCartStore.getState().setIngredientesExcluidos(item.productoId, excluidos);
                          }}
                          className="cursor-pointer"
                        />
                        {ing.ingrediente_nombre}
                      </label>
                    ))}
                  </div>
                )}
              </td>
              <td className="p-2">${Number(item.precio).toFixed(2)}</td>
              <td className="p-2 text-center">
                {/* Quantity controls with +/- buttons */}
                <span className="inline-flex items-center gap-1">
                  <button
                    onClick={() => handleDecrement(item.productoId)}
                    disabled={item.cantidad <= 1}
                    className="border border-gray-400 bg-white text-gray-700 hover:bg-gray-100 text-sm w-7 h-7 flex items-center justify-center rounded cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    -
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

      {/* Delivery address selector */}
      <div className="border-t pt-4 mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Direccion de entrega</h2>

        {loadingDirs ? (
          <p className="text-sm text-gray-400">Cargando direcciones...</p>
        ) : (
          <div className="flex items-center gap-2">
            <select
              value={direccionSelId === null ? "retiro" : direccionSelId}
              onChange={(e) => {
                const val = e.target.value;
                if (val === "nueva") {
                  setShowNewDir(true);
                } else if (val === "retiro") {
                  setDireccionSelId(null);
                } else {
                  setDireccionSelId(val ? Number(val) : null);
                }
              }}
              className="border border-gray-300 rounded px-3 py-2 text-sm flex-1 max-w-md"
            >
              <option value="retiro">
                Retirar en el local mas cercano (gratis)
              </option>
              {direcciones.length > 0 && (
                <optgroup label="--- Tus direcciones ---">
                  {direcciones.map((d) => (
                    <option key={d.id} value={d.id}>
                      {formatDireccion(d)}{d.es_principal ? " (Principal)" : ""}
                    </option>
                  ))}
                </optgroup>
              )}
              <option value="nueva" disabled={direcciones.length >= 10}>
                + Agregar nueva direccion
              </option>
            </select>
            {direccionSelId === null ? (
              <span className="text-xs text-green-600 font-medium whitespace-nowrap">
                Retiro en local (gratis)
              </span>
            ) : (
              <span className="text-xs text-blue-600 font-medium whitespace-nowrap">
                Con envio (+$50.00)
              </span>
            )}
          </div>
        )}
      </div>

      {/* Payment method selector */}
      <div className="border-t pt-4 mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">Metodo de pago</h2>
        <div className="flex gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="formaPago"
              value="EFECTIVO"
              checked={formaPago === "EFECTIVO"}
              onChange={() => setFormaPago("EFECTIVO")}
              className="cursor-pointer"
            />
            <span className="text-sm">Efectivo (contra entrega)</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="formaPago"
              value="MERCADOPAGO"
              checked={formaPago === "MERCADOPAGO"}
              onChange={() => setFormaPago("MERCADOPAGO")}
              className="cursor-pointer"
            />
            <span className="text-sm">MercadoPago (tarjeta/debito)</span>
          </label>
        </div>
      </div>

      {/* Subtotal and checkout button */}
      <div className="border-t pt-4 flex justify-between items-center">
        <div className="text-xl font-bold">
          Subtotal: <span className="text-blue-700">${total.toFixed(2)}</span>
          {direccionSelId && typeof direccionSelId === "number" && (
            <span className="text-base font-normal text-gray-500 ml-2">
              (+ $50.00 envio)
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

      {/* Stock warning modal */}
      {stockWarnings && (
        <StockWarningModal
          detalles={stockWarnings}
          onAdjust={handleStockAdjust}
          onClose={() => setStockWarnings(null)}
        />
      )}

      {/* New address modal */}
      {showNewDir && (
        <NuevaDireccionModal
          onClose={() => setShowNewDir(false)}
          onSave={handleCrearDireccion}
        />
      )}

      {/* MercadoPago checkout link modal */}
      {mpCheckoutUrl && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded p-6 w-full max-w-md text-center">
            <h2 className="text-lg font-bold mb-2">Pago con MercadoPago</h2>
            <p className="text-sm text-gray-600 mb-4">
              Su pedido fue creado. Para completar el pago, haga clic en el boton de abajo.
            </p>
            <a
              href={mpCheckoutUrl}
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded font-semibold hover:bg-blue-700 mb-3"
            >
              Ir a MercadoPago
            </a>
            <div>
              <button
                onClick={() => { setMpCheckoutUrl(null); navigate("/pedidos"); }}
                className="text-sm text-gray-500 underline cursor-pointer"
              >
                Ver mis pedidos
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
