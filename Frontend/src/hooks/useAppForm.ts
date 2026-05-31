import { useForm } from '@tanstack/react-form'
import type { FormOptions, FieldValidator, FieldValidators } from '@tanstack/react-form'

// ── Helper validators ──

export function required(message = 'Este campo es requerido'): FieldValidator<string | unknown[]> {
  return ({ value }) => {
    if (value === undefined || value === null) return message
    if (typeof value === 'string' && value.trim() === '') return message
    if (Array.isArray(value) && value.length === 0) return message
    return undefined
  }
}

export function minLength(min: number, message?: string): FieldValidator<string> {
  return ({ value }) => {
    if (typeof value !== 'string') return undefined
    return value.length >= min ? undefined : (message ?? `Mínimo ${min} caracteres`)
  }
}

export function maxLength(max: number, message?: string): FieldValidator<string> {
  return ({ value }) => {
    if (typeof value !== 'string') return undefined
    return value.length <= max ? undefined : (message ?? `Máximo ${max} caracteres`)
  }
}

export function email(message = 'Email inválido'): FieldValidator<string> {
  return ({ value }) => {
    if (typeof value !== 'string' || value === '') return undefined
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? undefined : message
  }
}

export function pattern(regex: RegExp, message: string): FieldValidator<string> {
  return ({ value }) => {
    if (typeof value !== 'string' || value === '') return undefined
    return regex.test(value) ? undefined : message
  }
}

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

export function useAppForm<TFormData extends Record<string, unknown>>(
  opts?: Omit<FormOptions<TFormData>, 'validators'> & {
    validators?: {
      onSubmit?: FieldValidator<TFormData>
    }
  }
) {
  return useForm<TFormData>({
    // Default behavior
    defaultValues: {} as TFormData,
    ...opts,
  })
}

// ── Tipos re-exportados para conveniencia ──

export type { FieldValidator, FieldValidators }
