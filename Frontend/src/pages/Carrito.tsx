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
import { pedidosApi } from "../api/pedidos";
import {
  direccionesApi,
  formatDireccion,
  type DireccionEntrega,
  type DireccionEntregaInput,
} from "../api/direcciones";
import { getAccessToken } from "../api/client";

/* ── Modal rápido para crear dirección desde el carrito ── */
function NuevaDireccionModal({
  onClose,
  onSave,
}: {
  onClose: () => void;
  onSave: (data: DireccionEntregaInput) => Promise<void>;
}) {
  const [alias, setAlias] = useState("");
  const [linea1, setLinea1] = useState("");
  const [linea2, setLinea2] = useState("");
  const [ciudad, setCiudad] = useState("");
  const [guardando, setGuardando] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!linea1.trim() || !ciudad.trim()) return;
    setGuardando(true);
    try {
      await onSave({
        alias: alias.trim() || null,
        linea1: linea1.trim(),
        linea2: linea2.trim() || null,
        ciudad: ciudad.trim(),
        es_principal: false,
      });
      onClose();
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white rounded p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-bold mb-4">Nueva Dirección de Entrega</h2>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Alias</label>
            <input
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="Ej: Casa, Trabajo..."
              maxLength={50}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Calle y Número <span className="text-red-500">*</span>
            </label>
            <input
              value={linea1}
              onChange={(e) => setLinea1(e.target.value)}
              placeholder="Av. Siempre Viva 123"
              required
              maxLength={100}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Piso / Dpto</label>
            <input
              value={linea2}
              onChange={(e) => setLinea2(e.target.value)}
              placeholder="Piso 3, Dpto B"
              maxLength={100}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Ciudad <span className="text-red-500">*</span>
            </label>
            <input
              value={ciudad}
              onChange={(e) => setCiudad(e.target.value)}
              placeholder="Ciudad"
              required
              maxLength={100}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
            />
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
              disabled={guardando || !linea1.trim() || !ciudad.trim()}
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

  const handleRemove = (productoId: number, medidaId?: number) => {
    setItems(removeFromCart(productoId, medidaId));
  };

  const handleIncrement = (productoId: number, medidaId?: number) => {
    const item = items.find((i) => i.productoId === productoId && i.medidaId === medidaId);
    if (item) {
      setItems(updateCantidad(productoId, item.cantidad + 1, medidaId));
    }
  };

  const handleDecrement = (productoId: number, medidaId?: number) => {
    const item = items.find((i) => i.productoId === productoId && i.medidaId === medidaId);
    if (item && item.cantidad > 1) {
      setItems(updateCantidad(productoId, item.cantidad - 1, medidaId));
    }
  };

  const handleRealizarPedido = async () => {
    if (items.length === 0) return;
    setEnviando(true);
    setError(null);

    try {
      const direccionId = typeof direccionSelId === "number" ? direccionSelId : undefined;
      await pedidosApi.create({
        forma_pago_codigo: "EFECTIVO",
        subtotal: getTotal(),
        descuento: 0,
        costo_envio: direccionId ? 50 : 0,
        direccion_id: direccionId,
        detalles: items.map((i) => ({
          producto_id: i.productoId,
          cantidad: i.cantidad,
          nombre_snapshot: i.nombre,
          precio_snapshot: i.precio,
          medida_id: i.medidaId ?? null,
        })),
      });

      clearCarrito();
      setItems([]);
      navigate("/pedidos");
    } catch (e) {
      if (e instanceof AxiosError && e.response?.data) {
        const detail = (e.response.data as { detail?: string }).detail;
        setError(detail ?? (e as Error).message);
      } else {
        setError((e as Error).message);
      }
    } finally {
      setEnviando(false);
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
            <tr key={`${item.productoId}-${item.medidaId ?? 'default'}`} className="hover:bg-gray-100 border-b">
              <td className="p-2">
                {item.nombre}
                {item.medidaNombre && (
                  <span className="text-gray-500 ml-1">— {item.medidaNombre}</span>
                )}
              </td>
              <td className="p-2">${Number(item.precio).toFixed(2)}</td>
              <td className="p-2 text-center">
                <span className="inline-flex items-center gap-1">
                  <button
                    onClick={() => handleDecrement(item.productoId, item.medidaId)}
                    disabled={item.cantidad <= 1}
                    className="border border-gray-400 bg-white text-gray-700 hover:bg-gray-100 text-sm w-7 h-7 flex items-center justify-center rounded cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    −
                  </button>
                  <span className="w-8 text-center font-mono font-semibold">
                    {item.cantidad}
                  </span>
                  <button
                    onClick={() => handleIncrement(item.productoId, item.medidaId)}
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
                  onClick={() => handleRemove(item.productoId, item.medidaId)}
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
