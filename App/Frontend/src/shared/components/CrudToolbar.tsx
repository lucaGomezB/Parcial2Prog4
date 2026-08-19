/**
 * CrudToolbar — Reusable CRUD toolbar with search, create, and optional export.
 *
 * Renders a responsive flex container with a search input on the left and
 * action buttons (create + optional export) on the right. Replaces duplicated
 * toolbar markup in 4 CRUD admin pages.
 *
 * Usage:
 *   <CrudToolbar
 *     searchValue={search}
 *     onSearchChange={setSearch}
 *     searchPlaceholder="Buscar productos..."
 *     onCreateClick={openCreateForm}
 *     createLabel="Nuevo producto"
 *     onExportClick={handleExport}
 *     exportLabel="Exportar Excel"
 *   />
 */
import type { ChangeEvent } from 'react'

// ── Types ──

export interface CrudToolbarProps {
  /** Current raw search input value (un-debounced). */
  searchValue: string
  /** Called when the search input value changes (raw, un-debounced). */
  onSearchChange: (value: string) => void
  /** Placeholder text for the search input. Default: "Buscar...". */
  searchPlaceholder?: string
  /** Called when the user clicks the create button. If omitted, the create button is not rendered. */
  onCreateClick?: () => void
  /** Label for the create button. Default: "Crear". */
  createLabel?: string
  /** Called when the user clicks the export button. If omitted, the export button is not rendered. */
  onExportClick?: () => void
  /** Label for the export button. Default: "Exportar". */
  exportLabel?: string
  /** When true, the export button is visually disabled. Default: false. */
  isExportDisabled?: boolean
}

// ── Component ──

export default function CrudToolbar({
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Buscar...',
  onCreateClick,
  createLabel = 'Crear',
  onExportClick,
  exportLabel = 'Exportar',
  isExportDisabled = false,
}: CrudToolbarProps) {
  function handleSearchChange(e: ChangeEvent<HTMLInputElement>) {
    onSearchChange(e.target.value)
  }

  return (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4">
      {/* ── Search input (left) ── */}
      <input
        type="text"
        value={searchValue}
        onChange={handleSearchChange}
        placeholder={searchPlaceholder}
        className="border border-gray-300 rounded px-3 py-1.5 text-sm w-full sm:w-auto min-w-[200px] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
      />

      {/* ── Action buttons (right) ── */}
      <div className="flex gap-2 w-full sm:w-auto">
        {onExportClick && (
          <button
            type="button"
            onClick={onExportClick}
            disabled={isExportDisabled}
            className={`px-3 py-1.5 rounded text-sm cursor-pointer ${
              isExportDisabled
                ? 'bg-green-300 text-white cursor-not-allowed'
                : 'bg-green-600 hover:bg-green-700 text-white'
            }`}
          >
            {exportLabel}
          </button>
        )}
        {onCreateClick && (
          <button
            type="button"
            onClick={onCreateClick}
            className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-700 text-white text-sm cursor-pointer"
          >
            {createLabel}
          </button>
        )}
      </div>
    </div>
  )
}
