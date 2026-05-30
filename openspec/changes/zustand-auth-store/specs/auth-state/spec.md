## ADDED Requirements

### Requirement: Store global de autenticación
El sistema DEBE proveer un store Zustand (`useAuthStore`) con el estado de autenticación, accesible desde cualquier componente sin prop drilling.

#### Scenario: Store expone usuario, roles, y estado de auth
- **WHEN** un componente consume `useAuthStore(s => s.user)`, `useAuthStore(s => s.roles)`, o `useAuthStore(s => s.isAuthenticated)`
- **THEN** obtiene los valores actuales y se re-renderiza cuando cambian

#### Scenario: Store se hidrata desde localStorage al crearse
- **WHEN** el store se inicializa (primera importación)
- **THEN** lee `getToken()` y `getUserInfo()` de localStorage y establece el estado inicial

### Requirement: Actions del store
El sistema DEBE proveer actions `login`, `logout`, `updateRoles` que actualicen el store y persistan en localStorage.

#### Scenario: login actualiza store y localStorage
- **WHEN** se llama `useAuthStore.getState().login(token, user)`
- **THEN** el store se actualiza con el usuario y roles, y `localStorage` se persiste con setToken/setUserInfo

#### Scenario: logout limpia store y localStorage
- **WHEN** se llama `useAuthStore.getState().logout()`
- **THEN** el store se limpia (user: null, roles: [], isAuthenticated: false) y localStorage se borra

### Requirement: Interceptor 401 usa el store
El sistema DEBE actualizar el response interceptor de Axios para usar el store en vez de eventos para el logout por expiración.

#### Scenario: 401 en refresh usa store.logout()
- **WHEN** el refresh token falla (401)
- **THEN** el interceptor llama `useAuthStore.getState().logout()` en vez de `clearAuth()` + evento `session:expired`

### Requirement: App.tsx consume el store
El sistema DEBE migrar App.tsx para obtener `userRoles` del store Zustand en vez de `useState`.

#### Scenario: userRoles viene del store
- **WHEN** App.tsx se monta o el store cambia
- **THEN** `userRoles` se obtiene de `useAuthStore(s => s.roles)` y el componente reacciona a cambios
