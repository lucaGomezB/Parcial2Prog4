## Context

`POST /auth/login` es público y sin protección. Cualquier IP puede probar passwords indefinidamente. El endpoint también carece de medidas como retardo progresivo o CAPTCHA, que son excesivas para este proyecto — un rate limit simple por IP con SlowAPI es suficiente.

## Goals / Non-Goals

**Goals:**
- Rate limit de 5 intentos por minuto por IP en `POST /auth/login`
- Respuesta clara con `429 Too Many Requests` cuando se excede el límite
- Fácil de extender a otros endpoints en el futuro

**Non-Goals:**
- No se agrega CAPTCHA ni bloqueo permanente de IPs
- No se limita `/auth/register` por ahora (a menos que se decida después)
- No se persisten los intentos en DB (solo en memoria, suficiente para rate limiting)

## Decisions

### 1. SlowAPI vs middleware custom
- **Decisión**: SlowAPI.
- **Por qué**: Es la librería estándar para FastAPI, usa `request.client.host` como key por defecto, se integra con decoradores, y maneja headers `Retry-After`. Hacerlo custom es reinventar la rueda.

### 2. Límite: 5 intentos por minuto
- **Decisión**: `"5/minute"` para login.
- **Por qué**: Un usuario legítimo rara vez hace más de 1-2 intentos seguidos. 5 por minuto da margen para errores de tipeo sin permitir fuerza bruta.
- **Alternativa**: `"10/minute"` — muy permisivo. `"3/minute"` — muy restrictivo (puede frustrar usuarios).

### 3. Key function: IP vs email+IP
- **Decisión**: IP únicamente (`get_remote_address`).
- **Por qué**: Limitar por email permitiría que un atacante intente con muchos emails desde una sola IP. Limitar por IP frena el ataque independientemente del email.

### 4. Almacenamiento: en memoria
- **Decisión**: Usar el backend por defecto de SlowAPI (memoria).
- **Por qué**: No necesitamos persistencia. Si el servidor se reinicia, los contadores se reinician. Suficiente para el caso de uso.

## Risks / Trade-offs

- **[Riesgo] Usuarios detrás de NAT compartida**: Varios usuarios desde la misma IP (ej: una facultad) comparten el límite. → **Mitigación**: 5/min es generoso para un usuario individual. Si hay abuso desde una IP compartida, se puede ajustar o considerar key por `email+IP`.
- **[Riesgo] SlowAPI agrega latencia**: Mínima — es un chequeo en memoria antes del handler.
- **[Trade-off] Sin bloqueo permanente**: Un atacante puede esperar 1 minuto y volver a intentar. → Para este proyecto es suficiente. Bloqueo permanente requiere persistencia y whitelist, que es overkill.
