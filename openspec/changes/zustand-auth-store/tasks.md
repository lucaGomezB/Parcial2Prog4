## 1. Setup

- [ ] 1.1 Instalar `zustand` como dependencia (`npm install zustand`)
- [ ] 1.2 Crear directorio `src/store/`

## 2. Store de autenticación

- [ ] 2.1 Crear `src/store/authStore.ts` con interfaz `AuthState` (user, roles, isAuthenticated, isLoading)
- [ ] 2.2 Implementar action `login(accessToken, user)` que persiste en localStorage y actualiza store
- [ ] 2.3 Implementar action `logout()` que limpia store y localStorage
- [ ] 2.4 Implementar action `setRoles(roles)` para actualizar roles sin hacer login completo
- [ ] 2.5 Hidratar store desde localStorage al inicializarse (leer getToken/getUserInfo)
- [ ] 2.6 Exportar selectores utilitarios: `useAuthUser`, `useAuthRoles`, `useIsAuthenticated`

## 3. Actualizar App.tsx

- [ ] 3.1 Reemplazar `const [userRoles, setUserRoles] = useState<string[] | null>(null)` por `useAuthStore(s => s.roles)`
- [ ] 3.2 Reemplazar `setUserRoles(user?.roles ?? [])` en el `useEffect` de verificación por `useAuthStore.getState().setRoles(...)`
- [ ] 3.3 Reemplazar `setUserRoles(null)` en logout por `useAuthStore.getState().logout()`
- [ ] 3.4 Actualizar el handler del evento `auth:login-required` para usar el store
- [ ] 3.5 Pasar `onLogin` de LoginConceptual para que llame al store en vez de `setUserRoles`

## 4. Actualizar client.ts (interceptor)

- [ ] 4.1 En el response interceptor 401 (refresh fallido), reemplazar `clearAuth()` + `window.dispatchEvent(session:expired)` por `useAuthStore.getState().logout()`
- [ ] 4.2 Verificar que el flujo de refresh queue siga funcionando

## 5. Compatibilidad legacy

- [ ] 5.1 Actualizar `getUserInfo()` en client.ts para que lea del store (no de localStorage directo)
- [ ] 5.2 Mantener `getAccessToken()` como está (sigue leyendo localStorage)
- [ ] 5.3 Verificar que `SessionTimeoutModal` funcione sin el evento `session:expired`

## 6. Limpieza

- [ ] 6.1 Eliminar variable `hasGestorRole` si ya no se usa (era dead code)
- [ ] 6.2 Verificar que no queden referencias a `session:expired` event en la app
- [ ] 6.3 Probar flujo completo: login → navegación → expiración → logout → redirect
