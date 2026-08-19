/**
 * Modal — Reusable modal dialog component.
 *
 * Replaces inline modal patterns (fixed overlay + white panel) used across
 * 14+ places in the project. Provides consistent backdrop, close button,
 * title, and scrollable body.
 *
 * Usage:
 *   <Modal open={show} onClose={() => setShow(false)} title="Editar Producto">
 *     <p>Modal content here</p>
 *   </Modal>
 */
import type { ReactNode } from 'react'

// ── Types ──

export interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  maxWidth?: string // default 'max-w-2xl'
  /** Optional footer rendered below children with border separator and flex layout for action buttons. */
  footer?: ReactNode
}

// ── Component ──

export default function Modal({ open, onClose, title, children, maxWidth = 'max-w-2xl', footer }: ModalProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className={`bg-white rounded p-6 w-full ${maxWidth} max-h-[80vh]`}
        style={{ overflowY: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold">{title}</h2>
          <button onClick={onClose} className="text-gray-500 text-xl cursor-pointer hover:text-gray-800">
            &times;
          </button>
        </div>

        {/* Body */}
        {children}

        {/* Footer (optional, backward-compatible) */}
        {footer && (
          <div className="flex justify-end gap-2 pt-4 border-t mt-4">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}
