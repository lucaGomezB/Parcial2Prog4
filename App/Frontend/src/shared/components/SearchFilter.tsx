/**
 * SearchFilter — Shared search input with internal debounce.
 *
 * Manages its own input state autonomously. Only emits the debounced
 * value via `onSearch` after the configured delay. Fires immediately
 * when the input is cleared (empty string).
 *
 * Props:
 *   - onSearch: callback with the debounced/final value
 *   - placeholder: input placeholder text (default "Filtrar...")
 *   - debounceMs: debounce delay in ms (default 300)
 *
 * Usage:
 *   <SearchFilter onSearch={(val) => setSearch(val)} />
 */
import { useState, useCallback, useRef, useEffect } from 'react'
import { useDebounce } from '@/shared/hooks/useDebounce'

export interface SearchFilterProps {
  onSearch: (value: string) => void
  placeholder?: string
  debounceMs?: number
}

export default function SearchFilter({
  onSearch,
  placeholder = 'Filtrar...',
  debounceMs = 300,
}: SearchFilterProps) {
  const [inputValue, setInputValue] = useState('')
  const debouncedValue = useDebounce(inputValue, debounceMs)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  // Fire onSearch when the debounced value stabilizes
  useEffect(() => {
    if (mountedRef.current) {
      onSearch(debouncedValue)
    }
  }, [debouncedValue, onSearch])

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value
      setInputValue(newValue)
      // Immediate callback when input is cleared
      if (newValue === '') {
        onSearch('')
      }
    },
    [onSearch],
  )

  return (
    <input
      type="text"
      value={inputValue}
      onChange={handleChange}
      placeholder={placeholder}
      className="border border-gray-300 rounded px-3 py-1.5 text-sm w-full sm:w-auto min-w-[200px] focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
    />
  )
}
