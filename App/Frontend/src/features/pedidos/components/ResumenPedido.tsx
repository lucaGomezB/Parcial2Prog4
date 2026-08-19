import { formatCurrency } from "@/shared/utils/formatCurrency";

/**
 * ResumenPedido — Order summary + submit button extracted from Carrito.
 *
 * Renders: total (with optional shipping breakdown), and action button.
 * Button text changes based on payment method and loading state.
 */
interface ResumenPedidoProps {
  subtotal: number
  costoEnvio: number
  enviando: boolean
  formaPago: string
  onSubmit: () => void
}

export function ResumenPedido({
  subtotal,
  costoEnvio,
  enviando,
  formaPago,
  onSubmit,
}: ResumenPedidoProps) {
  const esMercadoPago = formaPago === "MERCADOPAGO"
  const totalMostrado = esMercadoPago ? subtotal + costoEnvio : subtotal

  const buttonText = () => {
    if (enviando && esMercadoPago) return "Redirigiendo a MercadoPago..."
    if (enviando) return "Creando pedido..."
    if (esMercadoPago) return "Pagar con MercadoPago"
    return "Realizar Pedido"
  }

  return (
    <div className="border-t pt-4 flex justify-between items-center">
      <div className="text-xl font-bold">
        Total: <span className="text-blue-700">{formatCurrency(totalMostrado)}</span>
        {esMercadoPago && costoEnvio > 0 && (
          <span className="text-base font-normal text-gray-500 ml-2">(+ {formatCurrency(costoEnvio)} envio)</span>
        )}
      </div>
      <button
        onClick={onSubmit}
        disabled={enviando}
        className="bg-green-700 text-white px-6 py-2 rounded text-lg font-semibold cursor-pointer hover:bg-green-800 disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {buttonText()}
      </button>
    </div>
  )
}
