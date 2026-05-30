## Context

El estado de autenticación actual se distribuye entre:
- `client.ts`: Funciones que manipulan `localStorage` (`getToken`, `setUserInfo`, `clearAuth`, etc.)
- `App.tsx`: `useState<string[] | null>(null)` para `userRoles`, cargado via `GET /auth/me`
- `window` events: `session:expired` para notificar logout

Cuando ocurre un login, logout, o expiración, no hay una fuente única de verdad reactiva. Los componentes que necesitan el rol/usuario deben:
1. Leer `localStorage` directamente (no reactivo)
2. O recibirlo por props desde App.tsx (prop drilling)
3. O escuchar eventos manualmente

## Goals / Non-Goals

**Goals:**
- Store Zustand global para auth, accesible desde cualquier componente
- Reactivo: cambios en el store disparan re-renders donde se consumen
- Hidratado desde localStorage al arrancar
- El interceptor 401 usa el store para logout
- Migrar App.tsx a usar el store

**Non-Goals:**
- No se migran todos los consumos de `getUserInfo()` de una vez — pueden seguir usándolo (el store lo mantiene sincronizado)
- No se cambia la API de login/registro
- No se toca el backend

## Decisions

### 1. Store único vs store+context
- **Decisión**: Store único con Zustand. Sin React Context.
- **Por qué**: Zustand ya es global y reactivo. Context obligaría a wrappers y re-renders innecesarios.

### 2. Persistencia: middleware persist de Zustand vs manual
- **Decisión**: Sincronización manual con localStorage (como está hoy), sin middleware `persist`.
- **Por qué**: El middleware persist de Zustand tiene comportamientos asíncronos que complican la hidratación inicial. Como ya tenemos `localStorage` funcionando, el store se hidrata al crearse y escribe en `localStorage` en las actions.

### 3. Compatibilidad con funciones legacy
- **Decisión**: Las funciones `getUserInfo()`, `getAccessToken()`, etc. de `client.ts` se mantienen, pero ahora leen del store (no de localStorage directamente).
- **Por qué**: Evita tener que refactorizar todos los imports del proyecto de una vez. Migración progresiva.

### 4. Interceptor 401
- **Decisión**: El response interceptor usa `useAuthStore.getState().logout()` en vez de `clearAuth()` + evento `session:expired`.
- **Por qué**: Es más directo, no necesita eventos, y el store notifica a todos los suscriptores automáticamente.

## Risks / Trade-offs

- **[Riesgo] App.tsx se re-renderiza más de lo necesario**: Si usamos el store entero en vez de slices. → **Mitigación**: Usar selectores específicos (`useAuthStore(s => s.roles)`) para evitar re-renders.
- **[Riesgo] Inconsistencia transitoria**: Durante la migración, algunos componentes leen del store y otros de `localStorage`. → **Mitigación**: El store se hidrata desde localStorage y escribe en localStorage, así que siempre están sincronizados.
- **[Trade-off] Dependencia externa**: Zustand pesa ~1KB gzip. Es negligible y ampliamente adoptado.
