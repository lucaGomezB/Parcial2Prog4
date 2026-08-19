/**
 * Product filters store (Zustand).
 *
 * Centralises filter state for product listing pages (ProductosCliente, ProductosCRUD).
 * Persisted to localStorage via Zustand `persist` middleware with `partialize`
 * so only filter fields survive page reloads — pagination resets to defaults.
 *
 * State:
 *   - categoriaId: number | null — filter by category ID
 *   - searchTerm: string — text search filter
 *   - esProductoTerminado: boolean | null — producto-terminado-only filter (null = no filter)
 *   - skip: number — pagination offset
 *   - limit: number — page size
 */
import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

// ── Types ──

export interface FiltrosState {
  categoriaId: number | null
  searchTerm: string
  esProductoTerminado: boolean | null
  skip: number
  limit: number
}

export interface FiltrosActions {
  setCategoriaId: (id: number | null) => void
  setSearchTerm: (term: string) => void
  setEsProductoTerminado: (value: boolean | null) => void
  setPage: (skip: number) => void
  resetFilters: () => void
}

type FiltrosStore = FiltrosState & FiltrosActions

// ── Store ──

export const useFiltrosStore = create<FiltrosStore>()(
  persist(
    (set) => ({
      categoriaId: null,
      searchTerm: '',
      esProductoTerminado: null,
      skip: 0,
      limit: 10,

      setCategoriaId: (id) =>
        set({ categoriaId: id, skip: 0 }),

      setSearchTerm: (term) =>
        set({ searchTerm: term, skip: 0 }),

      setEsProductoTerminado: (value) =>
        set({ esProductoTerminado: value, skip: 0 }),

      setPage: (skip) => set({ skip }),

      resetFilters: () => {
        useFiltrosStore.persist.clearStorage()
        set({
          categoriaId: null,
          searchTerm: '',
          esProductoTerminado: null,
          skip: 0,
          limit: 10,
        })
      },
    }),
    {
      name: 'filtros-productos',
      storage: createJSONStorage(() => localStorage),
      // Only persist filter values, not pagination
      partialize: (state) => ({
        categoriaId: state.categoriaId,
        searchTerm: state.searchTerm,
        esProductoTerminado: state.esProductoTerminado,
      }),
    }
  )
)

// ── Selectors ──

export const useFiltrosCategoriaId = () => useFiltrosStore((s) => s.categoriaId)
export const useFiltrosSearchTerm = () => useFiltrosStore((s) => s.searchTerm)
export const useFiltrosEsProductoTerminado = () => useFiltrosStore((s) => s.esProductoTerminado)
export const useFiltrosSkip = () => useFiltrosStore((s) => s.skip)
export const useFiltrosLimit = () => useFiltrosStore((s) => s.limit)
