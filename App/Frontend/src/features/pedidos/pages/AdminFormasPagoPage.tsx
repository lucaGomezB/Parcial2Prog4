/**
 * AdminFormasPagoPage — Admin panel to enable/disable payment methods.
 * Uses TanStack Query for data fetching and mutations.
 */
import { AxiosError } from "axios";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/shared/api/client";
import { addToast } from "@/shared/components/Toast";
import { formatValidationErrors } from "@/shared/utils/fieldLabels";
import ErrorBanner from "@/shared/components/ErrorBanner";

interface FormaPago {
  codigo: string;
  descripcion: string;
  habilitado: boolean;
}

const queryKey = ["formas-pago", "admin"] as const;

/** Fetches ALL payment methods (including disabled) for the admin panel. */
function useFormasPagoAdmin() {
  return useQuery<FormaPago[]>({
    queryKey,
    queryFn: () => apiFetch<FormaPago[]>("/formas-pago/?incluir_deshabilitadas=true"),
  });
}

/** Toggles a payment method's habilitado flag via PATCH. */
function useToggleFormaPago() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ codigo, habilitado }: { codigo: string; habilitado: boolean }) =>
      apiFetch<FormaPago>(`/formas-pago/${codigo}`, {
        method: "PATCH",
        body: JSON.stringify({ habilitado }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey }),
    onError: (err: unknown) => {
      if (err instanceof AxiosError && err.response?.data) {
        const body = err.response.data as Record<string, unknown>;
        if (body.errors && Array.isArray(body.errors)) {
          const messages = formatValidationErrors(body.errors as Array<{ loc: string[]; msg: string; type: string }>);
          messages.forEach((m) => addToast("error", m));
        } else {
          addToast("error", "Error al actualizar la forma de pago");
        }
      } else {
        addToast("error", "Error al actualizar la forma de pago");
      }
    },
  });
}

export default function AdminFormasPagoPage() {
  const { data: formasPago = [], isLoading, isError, error } = useFormasPagoAdmin();
  const toggleMutation = useToggleFormaPago();

  const handleToggle = (codigo: string, current: boolean) => {
    toggleMutation.mutate({ codigo, habilitado: !current });
    addToast("exito", `Forma de pago ${!current ? "habilitada" : "deshabilitada"}`);
  };

  return (
    <div className="p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Gestion de Medios de Pago</h1>
      </div>
      <ErrorBanner isError={isError} error={error} message="Error al cargar" />
      {isLoading ? (
        <p className="text-gray-400">Cargando...</p>
      ) : (
        <div className="space-y-2 max-w-lg">
          {formasPago.map((fp) => (
            <div
              key={fp.codigo}
              className="flex items-center justify-between border border-gray-200 rounded p-3"
            >
              <div>
                <span className="font-semibold text-sm">{fp.descripcion}</span>
                <span className="text-xs text-gray-400 ml-2">({fp.codigo})</span>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={fp.habilitado}
                  onChange={() => handleToggle(fp.codigo, fp.habilitado)}
                />
                <div className="w-9 h-5 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-green-600" />
              </label>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
