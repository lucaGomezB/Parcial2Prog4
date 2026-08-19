/**
 * Shared authentication types.
 *
 * Extracted to a leaf module (imports nothing from the project) to break the
 * circular dependency between authStore.ts and client.ts:
 *
 *   shared/types/auth.ts    (leaf — no project imports)
 *         ▲           ▲
 *         │           │
 *   authStore.ts   client.ts  ──▶ authStore.ts
 *
 * Before: authStore.ts imported type UserInfo from client.ts, and client.ts
 * imported useAuthStore from authStore.ts → temporal dead zone on init.
 */

/** Public user profile returned by /auth/me. */
export interface UserInfo {
  id: number
  nombre: string
  apellido: string
  email: string
  celular?: string | null
  roles: string[]
}
