## ADDED Requirements

### Requirement: Rate limiting en login
El sistema DEBE limitar los intentos de autenticación en `POST /auth/login` a 5 requests por minuto por IP.

#### Scenario: Login exitoso dentro del límite
- **WHEN** un usuario envía credenciales válidas a `POST /auth/login` y no ha excedido 5 requests en el último minuto
- **THEN** el login se procesa normalmente y devuelve 200

#### Scenario: Límite excedido
- **WHEN** una IP envía más de 5 requests a `POST /auth/login` en menos de 1 minuto
- **THEN** el sistema responde con `429 Too Many Requests` y el header `Retry-After` indicando los segundos restantes

#### Scenario: Límite se reinicia después de 1 minuto
- **WHEN** una IP excede el límite y espera 1 minuto sin enviar requests
- **THEN** el contador se reinicia y puede volver a intentar login

### Requirement: Middleware global de rate limiting
El sistema DEBE tener SlowAPI configurado a nivel de aplicación para que los rate limits sean consistentes y extensibles.

#### Scenario: Limiter inicializado en startup
- **WHEN** la aplicación FastAPI inicia
- **THEN** `app.state.limiter` está configurado con `get_remote_address` como key function

#### Scenario: Error 429 tiene formato consistente
- **WHEN** cualquier endpoint con rate limit devuelve 429
- **THEN** el cuerpo de la respuesta incluye `{"detail": "Rate limit exceeded: <N> per <interval>"}` y el header `Retry-After`
