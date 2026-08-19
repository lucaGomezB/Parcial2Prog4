/**
 * useDebounce — Generic value debounce hook.
 *
 * Delays updating the returned value until `delay` ms of inactivity.
 * Cleans up pending timers on unmount to prevent state updates on
 * unmounted components.
 *
 * Usage:
 *   const debouncedSearch = useDebounce(searchInput, 300);
 *
 * Type parameter T allows debouncing any value type (string, number, object).
 */
import { useState, useEffect } from 'react'

export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => clearTimeout(timer)
  }, [value, delay])

  return debouncedValue
}
