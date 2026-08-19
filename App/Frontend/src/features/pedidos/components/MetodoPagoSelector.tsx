/**
 * MetodoPagoSelector — Payment method radio buttons extracted from Carrito.
 *
 * Renders radio buttons dynamically from the API response. Props receive
 * the current value and change handler from parent.
 *
 * States:
 *  - isLoading + no data → skeleton placeholder ("Cargando metodos de pago...")
 *  - empty array → "No hay metodos de pago disponibles"
 *  - data present → one radio button per enabled method
 */
import type { FormaPagoPublic } from "@/features/pedidos/api/formasPago";

interface MetodoPagoSelectorProps {
  formaPago: string;
  onChange: (value: string) => void;
  formasPago?: FormaPagoPublic[];
  isLoading?: boolean;
}

export function MetodoPagoSelector({
  formaPago,
  onChange,
  formasPago,
  isLoading,
}: MetodoPagoSelectorProps) {
  return (
    <div className="border-t pt-4 mb-4">
      <h2 className="text-sm font-semibold text-gray-700 mb-2">Metodo de pago</h2>

      {/* ── LOADING STATE ── */}
      {isLoading && (!formasPago || formasPago.length === 0) && (
        <p className="text-sm text-gray-400 animate-pulse">Cargando metodos de pago...</p>
      )}

      {/* ── EMPTY STATE ── */}
      {!isLoading && formasPago && formasPago.length === 0 && (
        <p className="text-sm text-red-600">No hay metodos de pago disponibles</p>
      )}

      {/* ── RADIO BUTTONS ── */}
      <div className="flex gap-4">
        {formasPago
          ?.filter((fp) => fp.habilitado) // defensive filter: show only enabled
          .map((fp) => (
            <label key={fp.codigo} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="formaPago"
                value={fp.codigo}
                checked={formaPago === fp.codigo}
                onChange={() => onChange(fp.codigo)}
                className="cursor-pointer"
              />
              <span className="text-sm">{fp.descripcion}</span>
            </label>
          ))}
      </div>
    </div>
  );
}
