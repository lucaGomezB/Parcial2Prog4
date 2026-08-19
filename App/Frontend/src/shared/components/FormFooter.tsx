/**
 * FormFooter — Standardized form action buttons.
 *
 * Renders Cancel (outlined) and Submit (blue) buttons with automatic label
 * switching based on form state. Replaces the duplicated button layouts
 * across all CRUD form pages.
 *
 * Usage:
 *   <FormFooter
 *     isSubmitting={isSubmitting}
 *     isEditing={!!editingId}
 *     onCancel={handleCloseForm}
 *   />
 */
import type { ReactNode } from "react";

export interface FormFooterProps {
  /** Whether the form is currently being submitted. */
  isSubmitting: boolean;
  /** Whether the form is editing an existing record (vs creating new). */
  isEditing: boolean;
  /** Called when the user clicks Cancel. */
  onCancel: () => void;
  /** Override the submit button label when creating. Default: "Crear". */
  createLabel?: string;
  /** Override the submit button label when editing. Default: "Actualizar". */
  updateLabel?: string;
  /** Override the submit button label while submitting. Default: "Guardando...". */
  submitLabel?: string;
  /** Optional additional CSS classes for the container div. */
  className?: string;
  /** Optional HTML form ID to associate the submit button with a form outside the component tree. */
  formId?: string;
}

export default function FormFooter({
  isSubmitting,
  isEditing,
  onCancel,
  createLabel = "Crear",
  updateLabel = "Actualizar",
  submitLabel = "Guardando...",
  className = "",
  formId,
}: FormFooterProps): ReactNode {
  const label = isSubmitting ? submitLabel : isEditing ? updateLabel : createLabel;

  return (
    <div className={`flex gap-2 ${className}`}>
      <button
        type="submit"
        form={formId}
        disabled={isSubmitting}
        className={`px-4 py-1 rounded cursor-pointer text-white ${
          isSubmitting
            ? "bg-blue-400 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700"
        }`}
      >
        {label}
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="bg-gray-400 text-white px-4 py-1 rounded cursor-pointer hover:bg-gray-500"
      >
        Cancelar
      </button>
    </div>
  );
}
