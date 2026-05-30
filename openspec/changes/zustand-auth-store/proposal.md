## Why

La autenticación se maneja con una mezcla de funciones que leen/escriben `localStorage` directamente (`client.ts`) más estado local `useState` en `App.tsx`. Esto no es reactivo: cuando el estado de auth cambia (login, logout, expiración), los componentes no se actualizan automáticamente. Además, cualquier componente que necesite saber el rol/usuario actual debe leer `localStorage` manualmente o recibirlo por props.

## What Changes

1. **Agregar dependencia** `zustand` al proyecto
2. **Crear store de auth** con Zustand: `src/store/authStore.ts`
3. **Migrar App.tsx** para usar el store en vez de `useState` para `userRoles`
4. **Actualizar client.ts** para que el interceptor 401 use el store (en vez de eventos)
5. **Componentes existentes** que usan `getUserInfo()` / `getAccessToken()` pueden seguir funcionando (el store se hidrata desde localStorage)
6. **No breaking**: las funciones legacy de `client.ts` se mantienen como compatibilidad

## Capabilities

### New Capabilities
- `auth-state`: Store global de autenticación con Zustand, reactivo, sincronizado con localStorage, accesible desde cualquier componente sin prop drilling.

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **Frontend/package.json**: Nueva dependencia `zustand`
- **Frontend/src/store/authStore.ts**: Store Zustand con estado, actions, hydratación desde localStorage
- **Frontend/src/App.tsx**: Reemplazar `useState` + `useEffect` por store + suscripción
- **Frontend/src/api/client.ts**: El interceptor 401 usa `useAuthStore.getState().logout()` en vez de `clearAuth()` + evento
- **Frontend/src/pages/**: Componentes que consumen roles pueden usar `useAuthStore(s => s.roles)` en vez de props
