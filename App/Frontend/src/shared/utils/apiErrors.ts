/**
 * apiErrors.ts — Decodes Axios error responses into a structured object.
 *
 * Pure utility function. No React imports, no side effects, no logging.
 * Replaces 5 nearly identical try/catch blocks across CRUD admin pages.
 *
 * Usage:
 *   const parsed = parseApiError(error)
 *   if (parsed.validationErrors.length > 0) setErrors(parsed.validationErrors)
 *   if (parsed.businessError === 'stock_insuficiente') handleStockError()
 *   toast.error(parsed.detail)
 */
import { isAxiosError } from 'axios'
import { formatValidationErrors } from '@/shared/utils/fieldLabels'

// ── Types ──

export interface ParsedApiError {
  /** Human-readable validation messages formatted via formatValidationErrors. Empty array if none. */
  validationErrors: string[]
  /** RFC 7807 detail message from the backend, or null. */
  detail: string | null
  /** Backend-specific business error code string (e.g. "stock_insuficiente"), or null. */
  businessError: string | null
  /** HTTP status code from the response, or null for non-HTTP errors. */
  status: number | null
}

// ── Public API ──

/**
 * Decodes any error value into a structured {@link ParsedApiError}.
 *
 * Handles Axios error responses (HTTP 400/422 with RFC 7807 Problem Details
 * or Pydantic validation errors) and non-Axios errors (network failures,
 * unexpected throws, null/undefined input).
 *
 * The function is pure: no side effects, no logging, no state mutation.
 * Each page controls how to display the parsed error.
 */
export function parseApiError(error: unknown): ParsedApiError {
  // Null / undefined guard
  if (error === null || error === undefined) {
    return {
      validationErrors: [],
      detail: 'Error desconocido',
      businessError: null,
      status: null,
    }
  }

  // Axios error: inspect response for structured data
  if (isAxiosError(error)) {
    const status = error.response?.status ?? null
    const data = error.response?.data

    // RFC 7807 Problem Details or Pydantic 422
    if (data && typeof data === 'object') {
      const detail: string | null =
        typeof (data as Record<string, unknown>).detail === 'string'
          ? ((data as Record<string, unknown>).detail as string)
          : null

      // Check both `businessError` and `error` fields (backend uses both conventions)
      const businessError: string | null =
        typeof (data as Record<string, unknown>).businessError === 'string'
          ? ((data as Record<string, unknown>).businessError as string)
          : typeof (data as Record<string, unknown>).error === 'string'
            ? ((data as Record<string, unknown>).error as string)
            : null

      // Pydantic validation errors (422): data.errors is an array
      const rawErrors = (data as Record<string, unknown>).errors
      const validationErrors = formatValidationErrors(
        Array.isArray(rawErrors) ? (rawErrors as Array<{ loc: string[]; msg: string; type: string }>) : undefined,
      )

      return { validationErrors, detail, businessError, status }
    }

    // Axios error without a structured response body (network error, timeout, etc.)
    return {
      validationErrors: [],
      detail: 'Error de conexion',
      businessError: null,
      status,
    }
  }

  // Non-Axios error (e.g. plain Error, string throw)
  if (error instanceof Error) {
    return {
      validationErrors: [],
      detail: error.message || 'Error de conexion',
      businessError: null,
      status: null,
    }
  }

  // Fallback for unexpected error shapes
  return {
    validationErrors: [],
    detail: 'Error de conexion',
    businessError: null,
    status: null,
  }
}
