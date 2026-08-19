/**
 * useCrudTable — Generic CRUD orchestration hook.
 *
 * Composes usePagination (existing shared hook) with search state, sort state,
 * and delete confirmation dialog state into a single return object.
 *
 * This hook is pure state composition — it does NOT import from any feature
 * module or TanStack Query type. Each page retains control over data fetching,
 * mutation logic, and error display.
 *
 * Usage:
 *   const crud = useCrudTable({ defaultLimit: 10, defaultSortBy: 'nombre' })
 *   const debouncedSearch = useDebounce(crud.search, 300)
 *   const { data, isLoading } = useQuery({ queryKey: [..., debouncedSearch, crud.skip, crud.limit] })
 *
 *   <CrudToolbar searchValue={crud.search} onSearchChange={crud.setSearch} ... />
 *   <DataTable sortBy={crud.sortBy} sortOrder={crud.sortOrder} onSort={crud.handleSort} ... />
 *   <ConfirmDialog open={crud.deleteConfirmOpen} ... />
 */
import { useState, useCallback } from 'react'
import { usePagination } from '@/shared/hooks/usePagination'

// ── Types ──

export interface UseCrudTableOptions {
  /** Initial page size. Default: 10. */
  defaultLimit?: number
  /** Initial sort column key. Default: undefined (no initial sort). */
  defaultSortBy?: string
  /** Initial sort direction. Default: "asc". */
  defaultSortOrder?: 'asc' | 'desc'
}

export interface UseCrudTableReturn {
  // ── Pagination (from usePagination) ──
  /** Current offset (0-based). */
  skip: number
  /** Current page size. */
  limit: number
  /** Go to a specific page offset. */
  handlePageChange: (skip: number) => void
  /** Change page size (resets skip to 0). */
  handleLimitChange: (limit: number) => void

  // ── Search ──
  /** Current raw search input value (un-debounced). */
  search: string
  /** Update the search input value. */
  setSearch: (value: string) => void

  // ── Sort ──
  /** Current sort column key, or undefined if no sort active. */
  sortBy: string | undefined
  /** Current sort direction. */
  sortOrder: 'asc' | 'desc'
  /** Handle a sort action. Toggles direction if same column, sets asc for new column. */
  handleSort: (sortBy: string, sortOrder: 'asc' | 'desc') => void

  // ── Delete confirmation ──
  /** Whether the delete confirmation dialog is open. */
  deleteConfirmOpen: boolean
  /** The item targeted for deletion, or null. */
  deleteTarget: { id: number; label: string } | null
  /** Open the delete confirmation dialog for a specific item. */
  openDeleteConfirm: (id: number, label: string) => void
  /** Close the delete confirmation dialog and clear the target. */
  closeDeleteConfirm: () => void
}

// ── Hook ──

export function useCrudTable(options: UseCrudTableOptions = {}): UseCrudTableReturn {
  const { defaultLimit = 10, defaultSortBy, defaultSortOrder = 'asc' } = options

  // ── Pagination ──
  const { skip, limit, handlePageChange, handleLimitChange } = usePagination(defaultLimit)

  // ── Search ──
  const [search, setSearch] = useState('')

  // ── Sort ──
  const [sortBy, setSortBy] = useState<string | undefined>(defaultSortBy)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(defaultSortOrder)

  const handleSort = useCallback(
    (newSortBy: string, newSortOrder: 'asc' | 'desc') => {
      setSortBy(newSortBy)
      setSortOrder(newSortOrder)
    },
    [],
  )

  // ── Delete confirmation ──
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{ id: number; label: string } | null>(null)

  const openDeleteConfirm = useCallback((id: number, label: string) => {
    setDeleteTarget({ id, label })
    setDeleteConfirmOpen(true)
  }, [])

  const closeDeleteConfirm = useCallback(() => {
    setDeleteConfirmOpen(false)
    setDeleteTarget(null)
  }, [])

  return {
    // Pagination
    skip,
    limit,
    handlePageChange,
    handleLimitChange,
    // Search
    search,
    setSearch,
    // Sort
    sortBy,
    sortOrder,
    handleSort,
    // Delete confirmation
    deleteConfirmOpen,
    deleteTarget,
    openDeleteConfirm,
    closeDeleteConfirm,
  }
}
