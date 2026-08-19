/**
 * RegistrarForm — Registration form component extracted from LoginConceptual.
 *
 * Owns its TanStack Form instance, loading/error states, and the full
 * registration flow (POST /auth/register + GET /auth/me). Calls onSuccess
 * after the user is authenticated so the parent can redirect.
 */
import { useState } from 'react'
import { apiFetch, setToken, setUserInfo } from '@/shared/api/client'
import { AxiosError } from 'axios'
import {
  useAppForm,
  composeValidators,
  required,
  email,
  minLength,
} from '@/shared/hooks/useAppForm'
import { formatValidationErrors } from '@/shared/utils/fieldLabels'

interface RegistrarFormProps {
  onSuccess: () => void
}

interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

interface UserInfo {
  id: number
  nombre: string
  apellido: string
  email: string
  celular?: string | null
  roles: string[]
}

interface RegisterFormValues {
  nombre: string
  apellido: string
  celular: string
  email: string
  password: string
  confirmPassword: string
}

export default function RegistrarForm({ onSuccess }: RegistrarFormProps) {
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const form = useAppForm<RegisterFormValues>({
    defaultValues: {
      nombre: '',
      apellido: '',
      celular: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
    onSubmit: async ({ value }: { value: RegisterFormValues }) => {
      setError('')
      setIsLoading(true)

      // Client-side password confirmation check before hitting the backend
      if (value.password !== value.confirmPassword) {
        setError('Las contraseñas no coinciden')
        setIsLoading(false)
        return
      }

      try {
        const response = await apiFetch<LoginResponse>('/auth/register', {
          method: 'POST',
          body: JSON.stringify({
            nombre: value.nombre.trim(),
            apellido: value.apellido.trim(),
            email: value.email.trim(),
            // Send null instead of empty string to keep the field absent on the backend
            celular: value.celular.trim() || null,
            password: value.password,
          }),
        })

        setToken(response.access_token, response.expires_in)

        // Fetch fresh user info and persist to store
        const userInfo = await apiFetch<UserInfo>('/auth/me')
        setUserInfo(userInfo)

        onSuccess()
      } catch (err: unknown) {
        console.error('Register error:', err)

        let errorMsg = ''
        if (err instanceof AxiosError && err.response?.data) {
          const body = err.response.data as Record<string, unknown>
          if (body.errors && Array.isArray(body.errors)) {
            const messages = formatValidationErrors(body.errors as Array<{ loc: string[]; msg: string; type: string }>)
            errorMsg = messages.join('\n')
          } else if (body.detail && typeof body.detail === 'string') {
            errorMsg = body.detail
          }
        }
        if (!errorMsg) {
          errorMsg = 'Error al crear la cuenta. Es posible que el email ya este registrado.'
        }
        setError(errorMsg)
      } finally {
        setIsLoading(false)
      }
    },
  })

  return (
    <>
      {/* Error banner */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-2 rounded mb-4 text-sm text-center">
          {error}
        </div>
      )}

      <form
        onSubmit={(e) => {
          e.preventDefault()
          e.stopPropagation()
          void form.handleSubmit()
        }}
        className="flex flex-col gap-4"
      >
        {/* Nombre + Apellido row */}
        <div className="flex gap-3">
          <form.Field
            name="nombre"
            validators={{ onChange: required() }}
          >
            {(field) => (
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  disabled={isLoading}
                  className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
                />
                {field.state.meta.errors.length > 0 && (
                  <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(', ')}</em>
                )}
              </div>
            )}
          </form.Field>
          <form.Field
            name="apellido"
            validators={{ onChange: required() }}
          >
            {(field) => (
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">Apellido</label>
                <input
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  disabled={isLoading}
                  className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
                />
                {field.state.meta.errors.length > 0 && (
                  <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(', ')}</em>
                )}
              </div>
            )}
          </form.Field>
        </div>

        {/* Celular */}
        <form.Field
          name="celular"
          validators={{ onChange: required() }}
        >
          {(field) => (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Celular</label>
              <input
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                disabled={isLoading}
                className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
              />
              {field.state.meta.errors.length > 0 && (
                <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(', ')}</em>
              )}
            </div>
          )}
        </form.Field>

        {/* Email */}
        <form.Field
          name="email"
          validators={{ onChange: composeValidators(required(), email()) }}
        >
          {(field) => (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
              <input
                type="email"
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
                disabled={isLoading}
              />
              {field.state.meta.errors.length > 0 && (
                <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(', ')}</em>
              )}
            </div>
          )}
        </form.Field>

        {/* Password with show/hide toggle */}
        <form.Field
          name="password"
          validators={{ onChange: composeValidators(required(), minLength(6)) }}
        >
          {(field) => (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Contrasena</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={field.state.value}
                  onChange={(e) => field.handleChange(e.target.value)}
                  onBlur={field.handleBlur}
                  placeholder="********"
                  className="w-full border border-gray-300 px-3 py-2 pr-10 rounded focus:outline-none focus:border-blue-500"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                  className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-500 hover:text-gray-700 cursor-pointer"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    // Eye-off icon when password is visible
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
                    </svg>
                  ) : (
                    // Eye icon when password is hidden
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  )}
                </button>
              </div>
              {field.state.meta.errors.length > 0 && (
                <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(', ')}</em>
              )}
            </div>
          )}
        </form.Field>

        {/* Confirm Password */}
        <form.Field
          name="confirmPassword"
          validators={{ onChange: required() }}
        >
          {(field) => (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar contrasena</label>
              <input
                type="password"
                value={field.state.value}
                onChange={(e) => field.handleChange(e.target.value)}
                onBlur={field.handleBlur}
                disabled={isLoading}
                className="w-full border border-gray-300 px-3 py-2 rounded focus:outline-none focus:border-blue-500"
              />
              {field.state.meta.errors.length > 0 && (
                <em className="text-red-500 text-xs mt-1 block">{field.state.meta.errors.join(', ')}</em>
              )}
            </div>
          )}
        </form.Field>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded mt-2 transition-colors cursor-pointer disabled:bg-blue-400 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Creando cuenta...' : 'Crear cuenta'}
        </button>
      </form>
    </>
  )
}
