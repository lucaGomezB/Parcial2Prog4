/**
 * ConfirmDialog — Standardized confirmation dialog wrapping the existing shared Modal.
 *
 * Replaces `window.confirm()` and inline confirm modals in 5 CRUD pages
 * with a controlled component that renders a title, message, and two action
 * buttons (confirm + cancel) in the Modal footer.
 *
 * Usage:
 *   <ConfirmDialog
 *     open={showConfirm}
 *     title="Eliminar producto"
 *     message={`¿Esta seguro de eliminar '${target?.label}'?`}
 *     variant="danger"
 *     onConfirm={handleDelete}
 *     onCancel={() => setShowConfirm(false)}
 *     isLoading={isDeleting}
 *   />
 */
import Modal from '@/shared/components/Modal'

// ── Types ──

export interface ConfirmDialogProps {
  /** Whether the dialog is visible. */
  open: boolean
  /** Dialog title displayed in the Modal header. */
  title: string
  /** Body message explaining what the user is confirming. */
  message: string
  /** Label for the confirm button. Default: "Eliminar". */
  confirmLabel?: string
  /** Label for the cancel button. Default: "Cancelar". */
  cancelLabel?: string
  /** Visual variant: "danger" = red confirm button, "warning" = yellow. Default: "danger". */
  variant?: 'danger' | 'warning'
  /** Called when the user clicks the confirm button. */
  onConfirm: () => void
  /** Called when the user clicks cancel, the close button, or the backdrop. */
  onCancel: () => void
  /** When true, both buttons are disabled (prevents double-clicks during mutation). */
  isLoading?: boolean
}

// ── Component ──

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Eliminar',
  cancelLabel = 'Cancelar',
  variant = 'danger',
  onConfirm,
  onCancel,
  isLoading = false,
}: ConfirmDialogProps) {
  const confirmButtonClass =
    variant === 'danger'
      ? 'bg-red-600 hover:bg-red-700 text-white'
      : 'bg-yellow-500 hover:bg-yellow-600 text-white'

  const disabledClass = 'opacity-50 cursor-not-allowed'

  const footer = (
    <>
      <button
        type="button"
        onClick={onCancel}
        disabled={isLoading}
        className={`px-4 py-2 rounded border border-gray-300 text-gray-700 bg-white hover:bg-gray-100 cursor-pointer ${isLoading ? disabledClass : ''}`}
      >
        {cancelLabel}
      </button>
      <button
        type="button"
        onClick={onConfirm}
        disabled={isLoading}
        className={`px-4 py-2 rounded cursor-pointer ${confirmButtonClass} ${isLoading ? disabledClass : ''}`}
      >
        {confirmLabel}
      </button>
    </>
  )

  return (
    <Modal open={open} onClose={onCancel} title={title} maxWidth="max-w-md" footer={footer}>
      <p className="text-gray-700">{message}</p>
    </Modal>
  )
}
