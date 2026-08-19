/**
 * DireccionSelector — Address selection component extracted from Carrito.
 *
 * Props receive all data from the parent; no shared form state.
 * When esRetiroLocal is true, shows a dropdown of company stores (locales)
 * as pickup points instead of personal delivery addresses.
 * Uses formatDireccion for display labels.
 */
import { useMemo } from 'react'
import { formatDireccion, type DireccionEntrega } from '@/features/pedidos/api/direcciones'
import { COSTO_ENVIO } from '@/features/pedidos/constants'
import { formatCurrency } from '@/shared/utils/formatCurrency'

interface DireccionSelectorProps {
  direccionSelId: number | "nueva" | null
  direcciones: DireccionEntrega[]
  loadingDirs: boolean
  esRetiroLocal: boolean
  ocultarRetiroLocal?: boolean
  onChange: (value: string) => void
  onNuevaDireccion: () => void
}

export function DireccionSelector({
  direccionSelId,
  direcciones,
  loadingDirs,
  esRetiroLocal,
  ocultarRetiroLocal = false,
  onChange,
  onNuevaDireccion,
}: DireccionSelectorProps) {
  const locales = useMemo(() => direcciones.filter((d) => d.es_local), [direcciones])
  const personales = useMemo(() => direcciones.filter((d) => !d.es_local), [direcciones])

  return (
    <div className="border-t pt-4 mb-4">
      <h2 className="text-sm font-semibold text-gray-700 mb-2">
        {esRetiroLocal ? "Locales disponibles para retiro" : "Direccion de entrega"}
      </h2>
      {loadingDirs ? (
        <p className="text-sm text-gray-400">Cargando direcciones...</p>
      ) : esRetiroLocal ? (
        <div className="flex flex-col sm:flex-row sm:items-center gap-2">
          <select
            value={direccionSelId === null ? "" : direccionSelId}
            onChange={(e) => onChange(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 text-sm w-full sm:flex-1"
          >
            {locales.length > 0 ? (
              locales.map((d) => (
                <option key={d.id} value={d.id}>
                  {`Local — ${d.linea1}, ${d.ciudad}`}
                </option>
              ))
            ) : (
              <option value="">No hay locales disponibles</option>
            )}
          </select>
          <span className="text-xs text-green-600 font-medium whitespace-nowrap">Retiro en local (gratis)</span>
        </div>
      ) : (
        <div className="flex flex-col sm:flex-row sm:items-center gap-2">
          <select
            value={direccionSelId === null ? "retiro" : direccionSelId}
            onChange={(e) => {
              const val = e.target.value;
              if (val === "nueva") onNuevaDireccion();
              else onChange(val);
            }}
            className="border border-gray-300 rounded px-3 py-2 text-sm w-full sm:flex-1"
          >
            {!ocultarRetiroLocal && <option value="retiro">Retirar en el local mas cercano (gratis)</option>}
            {personales.length > 0 && (
              <optgroup label="--- Tus direcciones ---">
                {personales.map((d) => (
                  <option key={d.id} value={d.id}>
                    {formatDireccion(d)}{d.es_principal ? " (Principal)" : ""}
                  </option>
                ))}
              </optgroup>
            )}
            <option value="nueva" disabled={personales.length >= 10}>
              + Agregar nueva direccion
            </option>
          </select>
          {direccionSelId === null ? (
            <span className="text-xs text-green-600 font-medium whitespace-nowrap">Retiro en local (gratis)</span>
          ) : (
            <span className="text-xs text-blue-600 font-medium whitespace-nowrap">Con envio (+{formatCurrency(COSTO_ENVIO)})</span>
          )}
        </div>
      )}
    </div>
  )
}
