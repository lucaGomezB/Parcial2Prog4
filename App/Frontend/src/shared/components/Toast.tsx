/**
 * Toast — Zustand-based toast notification system.
 *
 * Replaces inline `mostrarMensaje` + `useState<{tipo, texto}>` patterns
 * across the project. Any component can call `addToast('exito', 'texto')`
 * and the toast stack renders fixed at bottom-right with auto-dismiss (3s).
 *
 * Usage:
 *   import { addToast } from '@/shared/components/Toast'
 *   addToast('exito', 'Producto creado correctamente')
 *   addToast('error', 'Error al guardar')
 */
import { create } from 'zustand'
import { useEffect } from 'react'

// ── Types ──

export type ToastTipo = 'exito' | 'error' | 'warn'

export interface ToastItem {
  id: number
  tipo: ToastTipo
  texto: string
}

interface ToastState {
  toasts: ToastItem[]
  addToast: (tipo: ToastTipo, texto: string) => void
  removeToast: (id: number) => void
}

let _nextId = 0

// ── Store ──

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  addToast: (tipo, texto) => {
    const id = ++_nextId
    set((state) => ({ toasts: [...state.toasts, { id, tipo, texto }] }))
  },
  removeToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }))
  },
}))

// ── Public API ──

/** Imperative helper — call from anywhere, no hook needed. */
export const addToast = (tipo: ToastTipo, texto: string) => {
  useToastStore.getState().addToast(tipo, texto)
}

// ── Auto-dismiss wrapper ──

function ToastEntry({ toast }: { toast: ToastItem }) {
  const removeToast = useToastStore((s) => s.removeToast)

  useEffect(() => {
    const timer = setTimeout(() => removeToast(toast.id), 3000)
    return () => clearTimeout(timer)
  }, [toast.id, removeToast])

  const bgColor = toast.tipo === 'exito'
    ? 'bg-green-100 text-green-800 border-green-400'
    : toast.tipo === 'warn'
      ? 'bg-yellow-100 text-yellow-800 border-yellow-400'
      : 'bg-red-100 text-red-800 border-red-400'

  return (
    <div className={`p-3 rounded border shadow-lg ${bgColor} min-w-[280px] max-w-sm flex justify-between items-start gap-2`}>
      <span className="text-sm">{toast.texto}</span>
      <button
        onClick={() => removeToast(toast.id)}
        className="text-gray-500 hover:text-gray-800 text-lg leading-none cursor-pointer flex-shrink-0"
      >
        &times;
      </button>
    </div>
  )
}

// ── Renderer — mount once in App.tsx ──

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts)

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
      {toasts.map((t) => (
        <ToastEntry key={t.id} toast={t} />
      ))}
    </div>
  )
}
