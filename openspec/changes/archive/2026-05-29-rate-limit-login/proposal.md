## Why

El endpoint `POST /auth/login` no tiene ninguna protección contra fuerza bruta. Un atacante puede probar infinitas combinaciones de email/contraseña sin restricción. Con SlowAPI podemos limitar a N intentos por minuto por IP, mitigando ataques de diccionario sin afectar usuarios legítimos.

## What Changes

1. **Agregar SlowAPI** como dependencia
2. **Configurar middleware** de rate limiting en la app (app.state.limiter + exception handler 429)
3. **Aplicar rate limit** al endpoint `POST /auth/login`: 5 intentos por minuto por IP
4. **(Opcional)** Extender a `/auth/register` si se considera necesario

## Capabilities

### New Capabilities
- `rate-limiting`: Sistema de rate limiting con SlowAPI para endpoints críticos, inicialmente aplicado a login.

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **Backend/requirements.txt**: Nueva dependencia `slowapi`
- **Backend/main.py**: Agregar `Limiter` a `app.state` + exception handler para 429
- **Backend/modules/IdentidadYAcceso/Auth/router.py**: Decorador `@limiter.limit("5/minute")` en `POST /login`
- **Otros endpoints**: Si se quiere extender en el futuro, solo agregar el decorador
