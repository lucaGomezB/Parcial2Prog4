/**
 * PostPagoPage — Polling page shown after MercadoPago redirect.
 *
 * The user lands here after completing payment on MercadoPago.
 * This page polls GET /pagos/status every 2 seconds until either:
 *   - The Pedido is created (found) → redirects to /pedidos/{id}
 *   - 30 seconds elapse (timeout) → shows fallback with link to /pedidos
 *   - The payment was rejected (status=failure) → shows error with link to /carrito
 *
 * Query params:
 *   - external_reference: UUID shared between Pago, CarritoSnapshot, and Pedido
 *   - status: "approved" | "failure" | "pending" (from MP back_urls)
 */
import { useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { usePagoStatus } from "@/features/pedidos/hooks/usePagos";
import { useCartStore } from "@/shared/store/cartStore";
import { addToast } from "@/shared/components/Toast";
import ErrorBanner from "@/shared/components/ErrorBanner";

export default function PostPagoPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const externalReference = searchParams.get("external_reference");
  const paymentStatus = searchParams.get("status");

  // ── Guard: no external_reference → redirect to /pedidos ──
  useEffect(() => {
    if (!externalReference) {
      navigate("/pedidos", { replace: true });
    }
  }, [externalReference, navigate]);

  // If no external_reference, render nothing while redirecting
  if (!externalReference) {
    return null;
  }

  // ── Payment rejected ──
  if (paymentStatus === "failure") {
    return (
      <div className="max-w-lg mx-auto mt-16 p-6 text-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h1 className="text-xl font-bold text-red-800 mb-4">
            El pago no pudo ser procesado.
          </h1>
          <p className="text-red-600 mb-6">
            Intenta nuevamente o elige otro metodo de pago.
          </p>
          <a
            href="/carrito"
            className="inline-block bg-red-600 text-white px-6 py-2 rounded hover:bg-red-700 transition-colors"
          >
            Volver al carrito
          </a>
        </div>
      </div>
    );
  }

  // ── Normal flow: poll for pedido creation ──
  return <PollingContent externalReference={externalReference} />;
}

/** Internal component that renders the polling UI. */
function PollingContent({ externalReference }: { externalReference: string }) {
  const navigate = useNavigate();
  const { status, pedidoId, mpStatus, apiError, isPolling: _isPolling, isTimeout, error } =
    usePagoStatus(externalReference);

  // ── Pedido found → redirect ──
  useEffect(() => {
    if (status === "found" && pedidoId) {
      useCartStore.getState().clearCarrito();
      addToast("exito", `Pago confirmado! Tu pedido #${pedidoId} esta en proceso.`);
      navigate(`/pedidos/${pedidoId}`, { replace: true });
    }
  }, [status, pedidoId, navigate]);

  // ── Backend error during Pedido creation → show details ──
  if (status === "error" || apiError) {
    return (
      <div className="max-w-lg mx-auto mt-16 p-6 text-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h1 className="text-xl font-bold text-red-800 mb-4">
            No se pudo crear el pedido.
          </h1>
          <p className="text-red-600 mb-2">
            El pago fue aprobado pero ocurrio un error al procesar tu pedido.
          </p>
          {apiError && (
            <p className="text-xs text-red-400 mb-6 bg-red-100 p-2 rounded">
              {typeof apiError === 'string' ? apiError : JSON.stringify(apiError)}
            </p>
          )}
          <a
            href="/carrito"
            className="inline-block bg-red-600 text-white px-6 py-2 rounded hover:bg-red-700 transition-colors"
          >
            Volver al carrito
          </a>
        </div>
      </div>
    );
  }

  // ── Payment rejected or cancelled → show error immediately ──
  if (mpStatus === "rejected" || mpStatus === "cancelled") {
    return (
      <div className="max-w-lg mx-auto mt-16 p-6 text-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h1 className="text-xl font-bold text-red-800 mb-4">
            El pago fue rechazado o cancelado.
          </h1>
          <p className="text-red-600 mb-2">
            No se realizo ningun cobro. Podes intentar nuevamente desde el carrito.
          </p>
          <p className="text-xs text-red-400 mb-6">
            Estado: {mpStatus || "desconocido"}
          </p>
          <a
            href="/carrito"
            className="inline-block bg-red-600 text-white px-6 py-2 rounded hover:bg-red-700 transition-colors"
          >
            Volver al carrito
          </a>
        </div>
      </div>
    );
  }

  // ── Active polling ──
  const isActive = status !== "found" && !isTimeout && !error;

  if (isActive) {
    return (
      <div className="max-w-lg mx-auto mt-16 p-6 text-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <h1 className="text-xl font-bold text-gray-800">
            Procesando tu pago...
          </h1>
          <p className="text-gray-500">
            Esto puede tomar unos segundos.
          </p>
        </div>
      </div>
    );
  }

  // ── Timeout: max polling attempts reached without confirmation ──
  if (isTimeout) {
    return (
      <div className="max-w-lg mx-auto mt-16 p-6 text-center">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
          <h1 className="text-xl font-bold text-yellow-800 mb-4">
            No se pudo verificar el pago.
          </h1>
          <p className="text-yellow-600 mb-6">
            El pago puede estar siendo procesado. Si el cobro fue realizado,
            el pedido aparecera en tu historial en los proximos minutos.
            No realices el pago nuevamente hasta verificar.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <a
              href="/pedidos"
              className="inline-block bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition-colors"
            >
              Ver mis pedidos
            </a>
            <a
              href="/carrito"
              className="inline-block bg-gray-600 text-white px-6 py-2 rounded hover:bg-gray-700 transition-colors"
            >
              Volver al carrito
            </a>
          </div>
        </div>
      </div>
    );
  }

  // ── Error state ──
  if (error) {
    return (
      <div className="max-w-lg mx-auto mt-16 p-6">
        <ErrorBanner
          isError={true}
          message="Error al verificar el pago. Intenta nuevamente en unos segundos."
        />
        <div className="text-center mt-4">
          <a
            href="/pedidos"
            className="text-blue-600 underline hover:text-blue-800"
          >
            Ver mis pedidos
          </a>
        </div>
      </div>
    );
  }

  // ── Fallback (should not reach here) ──
  return (
    <div className="max-w-lg mx-auto mt-16 p-6 text-center">
      <p className="text-gray-500">Verificando el estado de tu pago...</p>
    </div>
  );
}
