> **Note de seguridad:** Durante la implementación se decidió eliminar toda persistencia en `localStorage` de datos de autenticación (access token, user info, roles). Ahora:
> - Access token vive SOLO en memoria (Zustand). Se obtiene al cargar la página vía `POST /auth/refresh` (cookie httpOnly).
> - User info se pide a `GET /auth/me` después del refresh.
> - Las funciones legacy (`getAccessToken`, `setToken`, etc.) ahora apuntan al store.
> - `localStorage` ya NO contiene secretos de sesión. La cookie httpOnly del refresh token es la única persistencia.

## 1. Setup

- [x] 1.1 Instalar `zustand` como dependencia (`npm install zustand`)
- [x] 1.2 Crear directorio `src/store/`
- [x] 2.1 Crear `src/store/authStore.ts` con interfaz `AuthState` (user, roles, isAuthenticated, isLoading)
- [x] 2.2 Implementar action `login(accessToken, user)` que persiste en localStorage y actualiza store
- [x] 2.3 Implementar action `logout()` que limpia store y localStorage
- [x] 2.4 Implementar action `setRoles(roles)` para actualizar roles sin hacer login completo
- [x] 2.5 Hidratar store desde localStorage al inicializarse (leer getToken/getUserInfo)
- [x] 2.6 Exportar selectores utilitarios: `useAuthUser`, `useAuthRoles`, `useIsAuthenticated`

## 3. Actualizar App.tsx

- [x] 3.1 Reemplazar `const [userRoles, setUserRoles] = useState<string[] | null>(null)` por `useAuthStore(s => s.roles)`
- [x] 3.2 Reemplazar `setUserRoles(user?.roles ?? [])` en el `useEffect` de verificación por `useAuthStore.getState().setRoles(...)`
- [x] 3.3 Reemplazar `setUserRoles(null)` en logout por `useAuthStore.getState().logout()`
- [x] 3.4 Eliminar handler del evento `auth:login-required` (el store es reactivo, no necesita eventos)
- [x] 3.5 Pasar `onLogin` de LoginConceptual para que llame `syncFromStorage()` en vez de `setUserRoles`

## 4. Actualizar client.ts (interceptor)

- [x] 4.1 En el response interceptor 401 (refresh fallido), reemplazar `clearAuth()` + `window.dispatchEvent(session:expired)` por `useAuthStore.getState().logout()`
- [x] 4.2 Verificar que el flujo de refresh queue siga funcionando (sin cambios en la queue, solo cambió el handler de error)

## 5. Compatibilidad legacy

- [x] 5.1 Actualizar `getUserInfo()` en client.ts para que intente desde el store primero, con fallback a localStorage (circular dep safety)
- [x] 5.2 Mantener `getAccessToken()` como está (sigue leyendo localStorage)
- [x] 5.3 Actualizar `SessionTimeoutModal` para usar `useAuthStore.getState().logout()` en vez de `clearAuth()` + evento `session:expired`

## 6. Limpieza

- [x] 6.1 Eliminar variable `hasGestorRole` si ya no se usa (era dead code) — ya no existe en el código
- [x] 6.2 Verificar que no queden referencias a `session:expired` ni `auth:login-required` events — 0 referencias
- [x] 6.3 Compilación TypeScript exitosa (`tsc --noEmit` sin errores)
