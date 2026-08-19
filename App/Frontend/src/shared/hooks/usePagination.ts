/**
 * usePagination — Shared pagination state hook.
 *
 * Manages `skip` and `limit` state with handler functions following
 * the same pattern used across all CRUD pages.
 *
 * `handleLimitChange` resets `skip` to 0 when the page size changes,
 * preventing out-of-range offsets.
 *
 * Usage:
 *   const { skip, limit, handlePageChange, handleLimitChange } = usePagination(10);
 */
import { useState, useCallback } from 'react'

export function usePagination(defaultLimit: number = 10) {
  const [skip, setSkip] = useState(0)
  const [limit, setLimit] = useState(defaultLimit)

  const handlePageChange = useCallback((newSkip: number) => setSkip(newSkip), [])
  const handleLimitChange = useCallback((newLimit: number) => {
    setLimit(newLimit)
    setSkip(0)
  }, [])

  return { skip, limit, handlePageChange, handleLimitChange }
}
