/**
 * Application-wide form utilities and hook.
 *
 * Provides a pre-configured wrapper around @tanstack/react-form with:
 *  - Common validators (required, minLength, maxLength, email, regex pattern).
 *  - A `composeValidators` helper to chain multiple validators on a single field.
 *  - A base `useAppForm` hook that sets sensible defaults (empty defaultValues)
 *    and accepts the full TanStack Form options for customisation.
 *
 * Usage:
 *   const form = useAppForm<MyFormData>({
 *     validators: { onSubmit: myOnSubmitValidator },
 *     onSubmit: async (values) => { ... },
 *   });
 *
 * Field validation:
 *   <form.Field
 *     name="email"
 *     validators={{
 *       onChange: composeValidators(required(), email()),
 *     }}
 *   />
 */
import { useForm } from '@tanstack/react-form'
import type { FormOptions, FieldValidator, FieldValidators } from '@tanstack/react-form'

// ── Helper validators ──

/**
 * Returns a validator that rejects undefined, null, empty string, or empty array values.
 * @param message - Custom error message (default: "Este campo es requerido").
 */
export function required(message = 'Este campo es requerido'): FieldValidator<string | unknown[]> {
  return ({ value }) => {
    if (value === undefined || value === null) return message
    if (typeof value === 'string' && value.trim() === '') return message
    if (Array.isArray(value) && value.length === 0) return message
    return undefined
  }
}

/**
 * Returns a validator that enforces a minimum string length.
 * Does not validate non-string values (returns undefined for those).
 */
export function minLength(min: number, message?: string): FieldValidator<string> {
  return ({ value }) => {
    if (typeof value !== 'string') return undefined
    return value.length >= min ? undefined : (message ?? `Minimo ${min} caracteres`)
  }
}

/**
 * Returns a validator that enforces a maximum string length.
 * Does not validate non-string values.
 */
export function maxLength(max: number, message?: string): FieldValidator<string> {
  return ({ value }) => {
    if (typeof value !== 'string') return undefined
    return value.length <= max ? undefined : (message ?? `Maximo ${max} caracteres`)
  }
}

/**
 * Returns a validator that checks for a basic email format (regex-based).
 * Empty strings are skipped (no error) to allow optional email fields.
 */
export function email(message = 'Email invalido'): FieldValidator<string> {
  return ({ value }) => {
    if (typeof value !== 'string' || value === '') return undefined
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? undefined : message
  }
}

/**
 * Returns a validator that tests the value against a custom regex pattern.
 * Empty strings are skipped (no error).
 */
export function pattern(regex: RegExp, message: string): FieldValidator<string> {
  return ({ value }) => {
    if (typeof value !== 'string' || value === '') return undefined
    return regex.test(value) ? undefined : message
  }
}

/**
 * Chains multiple validators together. Returns the first error encountered,
 * or undefined if all validators pass.
 *
 * This is equivalent to a logical AND over validators:
 *   composeValidators(required(), minLength(3), maxLength(50))
 */
export function composeValidators<T>(...validators: FieldValidator<T>[]): FieldValidator<T> {
  return (props) => {
    for (const v of validators) {
      const error = v(props)
      if (error) return error
    }
    return undefined
  }
}

// ── Hook base ──

/**
 * Pre-configured wrapper around @tanstack/react-form's useForm hook.
 *
 * Sets an empty `defaultValues` as the baseline so that fields with no
 * explicit default are initialised to undefined rather than causing runtime
 * errors. Callers can override this and any other FormOptions via `opts`.
 *
 * @typeParam TFormData - Record type matching the form's field names and value types.
 * @param opts - Partial FormOptions to merge on top of defaults.
 * @returns The TanStack Form instance with full API (handleSubmit, Field, etc.).
 */
export function useAppForm<TFormData extends Record<string, unknown>>(
  opts?: Omit<FormOptions<TFormData>, 'validators'> & {
    validators?: {
      onSubmit?: FieldValidator<TFormData>
    }
  }
) {
  return useForm<TFormData>({
    // Default behavior: empty defaultValues to avoid undefined reference errors.
    defaultValues: {} as TFormData,
    ...opts,
  })
}

// ── Types re-exported for convenience ──

export type { FieldValidator, FieldValidators }
