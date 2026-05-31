## ADDED Requirements

### Requirement: Store global de autenticación
El sistema DEBE proveer un store Zustand (`useAuthStore`) con el estado de autenticación en memoria, accesible desde cualquier componente sin prop drilling.

#### Scenario: Store expone usuario, roles, access token, y estado de auth
- **WHEN** un componente consume `useAuthStore(s => s.user)`, `useAuthStore(s => s.roles)`, o `useAuthStore(s => s.isAuthenticated)`
- **THEN** obtiene los valores actuales y se re-renderiza cuando cambian

#### Scenario: Store se inicializa vacío — no hay datos persistentes en localStorage
- **WHEN** el store se inicializa (primera importación)
- **THEN** `user: null`, `roles: null`, `accessToken: null`, `isAuthenticated: false`
- **THEN** ningún secreto de sesión está en localStorage (solo cookie httpOnly del refresh token)

### Requirement: Actions del store
El sistema DEBE proveer actions `login`, `logout`, `setRoles`, `setSession`, `setUser` que actualicen el store en memoria.

#### Scenario: login actualiza store (sin localStorage)
- **WHEN** se llama `useAuthStore.getState().login(token, expiresIn, user)`
- **THEN** el store se actualiza con accessToken, expiresAt, usuario y roles
- **THEN** NO se escribe en localStorage

#### Scenario: logout limpia store (sin localStorage)
- **WHEN** se llama `useAuthStore.getState().logout()`
- **THEN** el store se limpia (todo a null/false)
- **THEN** NO se accede a localStorage

### Requirement: Bootstrapping via /auth/refresh
Al cargar la página, el sistema DEBE intentar renovar la sesión llamando a `POST /auth/refresh` que usa la cookie httpOnly del refresh token.

#### Scenario: Refresh exitoso → /auth/me → autenticado
- **WHEN** la página se carga y hay una cookie httpOnly de refresh token válida
- **THEN** `POST /auth/refresh` retorna un nuevo access token
- **THEN** se almacena en el store via `setSession()`
- **THEN** `GET /auth/me` obtiene los datos del usuario
- **THEN** se almacenan en el store via `setUser()`
- **THEN** la UI se muestra como autenticada

#### Scenario: Refresh falla → invitado
- **WHEN** la página se carga y NO hay cookie de refresh token (expirada o nunca existió)
- **THEN** `POST /auth/refresh` falla con 401
- **THEN** el store se pone en modo invitado (`roles: []`)
- **THEN** la UI se muestra como invitado (catálogo público)

### Requirement: Interceptor 401 usa el store
El sistema DEBE actualizar el response interceptor de Axios para usar el store en vez de eventos para el logout por expiración.

#### Scenario: 401 en refresh usa store.logout()
- **WHEN** el refresh token falla (401) durante una petición
- **THEN** el interceptor llama `useAuthStore.getState().logout()` en vez de `clearAuth()` + evento `session:expired`

### Requirement: App.tsx consume el store
El sistema DEBE migrar App.tsx para obtener `userRoles` del store Zustand en vez de `useState`.

#### Scenario: roles reactivos desde el store
- **WHEN** App.tsx se monta o el store cambia
- **THEN** `roles` se obtiene de `useAuthStore(s => s.roles)` y el componente reacciona a cambios

#### Scenario: roles = null → login, roles = [] → invitado, roles = [...] → autenticado
- **WHEN** `roles === null` y la verificación inicial terminó
- **THEN** se muestra la página de login
- **WHEN** `roles === []`
- **THEN** se muestra la vista de invitado (catálogo público)
- **WHEN** `roles === ['ADMIN']` (o cualquier rol)
- **THEN** se muestra la UI según los roles del usuario
