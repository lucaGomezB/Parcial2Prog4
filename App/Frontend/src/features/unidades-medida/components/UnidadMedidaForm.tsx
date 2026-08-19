/**
 * UnidadMedidaForm — Create/Edit form for measurement units.
 *
 * Used as an inline form (not a modal) embedded in the admin page.
 * When editingId is set, the form pre-fills with existing data and submits a PUT.
 * When editingId is null, the form is blank and submits a POST.
 */
import { useMemo } from "react";
import { useStore } from "@tanstack/react-form";
import { useAppForm, required, minValue } from "@/shared/hooks/useAppForm";
import type { UnidadMedidaCreate } from "@/features/unidades-medida/types";
import type { UnidadMedidaTipo } from "@/features/unidades-medida/types";
import FormFooter from "@/shared/components/FormFooter";
import DecimalInput from "@/shared/components/DecimalInput";

const TIPO_OPTIONS: { value: UnidadMedidaTipo; label: string }[] = [
  { value: "masa", label: "Masa" },
  { value: "volumen", label: "Volumen" },
  { value: "unidad", label: "Unidad" },
  { value: "area", label: "Area" },
];

const BASE_UNIT_MAP: Record<UnidadMedidaTipo, { nombre: string; simbolo: string }> = {
  masa:     { nombre: "gramo",   simbolo: "g" },
  volumen:  { nombre: "mililitro", simbolo: "mL" },
  unidad:   { nombre: "porcion", simbolo: "unidad" },
  area:     { nombre: "metro cuadrado", simbolo: "m²" },
};

interface UnidadMedidaFormProps {
  editingId: number | null;
  initialValues?: UnidadMedidaCreate;
  onSubmit: (data: UnidadMedidaCreate) => Promise<void>;
  onCancel: () => void;
  submitting: boolean;
}

export default function UnidadMedidaForm({
  editingId,
  initialValues,
  onSubmit: _onSubmit,
  onCancel,
  submitting,
}: UnidadMedidaFormProps) {
  const form = useAppForm<UnidadMedidaCreate>({
    defaultValues: initialValues ?? { nombre: "", simbolo: "", tipo: "masa", factor_conversion: 1.0 },
    onSubmit: async ({ value }: { value: UnidadMedidaCreate }) => {
      await _onSubmit(value);
    },
  });

  // ── Watch form values for dynamic conversion explanation ──
  const watchedTipo = useStore(form.store, (s) => s.values.tipo ?? "masa");
  const watchedSimbolo = useStore(form.store, (s) => s.values.simbolo ?? "");
  const watchedFactor = useStore(form.store, (s) => s.values.factor_conversion ?? 1.0);

  const conversionHint = useMemo(() => {
    const baseUnit = BASE_UNIT_MAP[watchedTipo];
    if (!baseUnit) return null;
    const factorNum = Number(watchedFactor);
    if (factorNum === 1) {
      return `Unidad base de ${watchedTipo} (1 ${baseUnit.simbolo})`;
    }
    const simbolo = watchedSimbolo || "?";
    return `1 ${simbolo} = ${factorNum} ${baseUnit.simbolo}  (equivale a ${factorNum} ${baseUnit.nombre}s)`;
  }, [watchedTipo, watchedSimbolo, watchedFactor]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
      className="border p-4 mb-4 rounded bg-gray-50 grid grid-cols-2 gap-3"
    >
      <div>
        <label className="block text-sm font-medium">Nombre</label>
        <form.Field name="nombre" validators={{ onChange: required() }}>
          {(field) => (
            <>
            <input
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              maxLength={50}
              className="border px-2 py-1 rounded w-full"
              placeholder="e.g. kilogramo"
            />
            <span className={`text-xs ${(field.state.value?.length ?? 0) >= 50 ? 'text-red-600' : 'text-gray-400'}`}>
              {field.state.value?.length ?? 0} / 50 caracteres
            </span>
            {field.state.meta.errors && (
              <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
            )}
            </>
          )}
        </form.Field>
      </div>

      <div>
        <label className="block text-sm font-medium">Simbolo</label>
        <form.Field name="simbolo" validators={{ onChange: required() }}>
          {(field) => (
            <>
            <input
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value)}
              onBlur={field.handleBlur}
              maxLength={10}
              className="border px-2 py-1 rounded w-full"
              placeholder="e.g. kg"
            />
            <span className={`text-xs ${(field.state.value?.length ?? 0) >= 10 ? 'text-red-600' : 'text-gray-400'}`}>
              {field.state.value?.length ?? 0} / 10 caracteres
            </span>
            {field.state.meta.errors && (
              <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
            )}
            </>
          )}
        </form.Field>
      </div>

      <div>
        <label className="block text-sm font-medium">Tipo</label>
        <form.Field name="tipo">
          {(field) => (
            <>
            <select
              value={field.state.value}
              onChange={(e) => field.handleChange(e.target.value as UnidadMedidaTipo)}
              className="border px-2 py-1 rounded w-full"
            >
              {TIPO_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {field.state.meta.errors && (
              <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
            )}
            </>
          )}
        </form.Field>
      </div>

      <div>
        <label className="block text-sm font-medium">Factor de Conversion</label>
        <form.Field name="factor_conversion" validators={{ onChange: minValue(0.001, 'Debe ser mayor a 0') }}>
          {(field) => (
            <>
            <div className="flex items-center gap-1">
              <span className="text-gray-500 font-medium text-lg leading-none">x</span>
              <DecimalInput
                value={field.state.value ?? 1.0}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
                decimals={3}
                min={0.001}
                step={0.001}
                width="min-w-[10ch]"
              />
            </div>
            {conversionHint && (
              <p className="text-xs text-gray-500 mt-1">{conversionHint}</p>
            )}
            {field.state.meta.errors && (
              <p className="text-red-500 text-sm mt-1">{field.state.meta.errors}</p>
            )}
            </>
          )}
        </form.Field>
      </div>

      <div className="col-span-2 mt-2">
        <FormFooter
          isSubmitting={submitting}
          isEditing={!!editingId}
          onCancel={onCancel}
        />
      </div>
    </form>
  );
}
