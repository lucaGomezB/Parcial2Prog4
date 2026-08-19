# api_middlewares_testing

API de ejemplo con **FastAPI + SQLModel + PostgreSQL** que demuestra:

1. **Middlewares** (Logging, Timing, Rate Limiting).
2. **Exception Handlers globales** (formato JSON unificado).
3. **JWT en cookie HttpOnly** con bcrypt y RBAC.
4. **Suite de tests** con pytest + TestClient (unit + integration).
---

## Estructura

```
api_middlewares_testing/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Entry point: lifespan, middlewares, routers
│   ├── core/
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── database.py          # Engine + get_session
│   │   ├── security.py          # bcrypt + JWT
│   │   ├── deps.py              # get_current_user, require_role
│   │   ├── logger.py            # setup_logging + get_logger
│   │   ├── base_repository.py   # CRUD genérico
│   │   ├── unit_of_work.py      # UoW base
│   │   ├── middleware/
│   │   │   ├── logging_middleware.py   # X-Request-ID
│   │   │   └── timing_middleware.py    # X-Response-Time-ms
│   │   ├── exceptions/
│   │   │   ├── custom_exceptions.py    # AppError + 6 subclases
│   │   │   └── exception_handlers.py   # 5 handlers
│   │   └── rate_limit/
│   │       ├── rate_limiter.py         # TokenBucket + RateLimiter
│   │       └── rate_limit_middleware.py
│   ├── db/
│   │   └── seed.py              # Admin inicial + productos de ejemplo
│   └── modules/
│       ├── usuarios/            # Auth + gestión de usuarios
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── repository.py
│       │   ├── unit_of_work.py
│       │   ├── service.py
│       │   └── router.py
│       └── productos/           # CRUD de productos
│           ├── models.py
│           ├── schemas.py
│           ├── repository.py
│           ├── unit_of_work.py
│           ├── service.py
│           └── router.py
├── tests/
│   ├── conftest.py              # Fixtures compartidos
│   ├── unit/
│   │   └── test_rate_limiter.py
│   └── integration/
│       ├── test_middlewares.py
│       ├── test_exception_handlers.py
│       ├── test_rate_limit.py
│       ├── test_auth.py
│       └── test_productos.py
├── .env                         # Config de desarrollo
├── .env.test                    # Config para tests
├── pytest.ini                   # Configuración de pytest
├── requirements.txt
├── docker-compose.yml           # PostgreSQL para dev
└── README.md
```

---

## Arquitectura (capas)

```
Router → Service → UnitOfWork → Repository → Model
(HTTP)   (lógica)   (UoW)        (queries)    (DB)
```

- **Router**: HTTP puro. Parsea body, llama al Service, devuelve JSON.
- **Service**: lógica de negocio. Lanza excepciones de dominio.
- **UnitOfWork**: maneja la transacción (commit/rollback).
- **Repository**: queries a la DB.
- **Model**: la tabla (SQLModel).

El **Service** recibe la `Session` en su `__init__` (inyectada por FastAPI) y abre un UoW con `with ... as uow:` por cada método.

---

## Tests

### Correr toda la suite

```powershell
pytest
```

### Solo unit tests (rápido, sin DB)

```powershell
pytest tests/unit/
```

### Solo integration tests

```powershell
pytest tests/integration/
```

### Con cobertura

```powershell
pytest --cov=app --cov-report=term-missing
```

### Tests específicos

```powershell
pytest tests/integration/test_auth.py -v
pytest -k "test_login"
```

---

## Endpoints principales

### Auth
- `POST /usuarios/register` — registrar usuario nuevo.
- `POST /usuarios/token` — login (form OAuth2). Setea cookie `access_token`.
- `POST /usuarios/logout` — borrar cookie.
- `GET /usuarios/me` — info del usuario actual.
- `GET /usuarios/` — listar (solo admin).
- `GET /usuarios/{id}` — ver perfil.
- `PATCH /usuarios/{id}` — actualizar.
- `POST /usuarios/admin/usuarios/{id}/activar` — activar (admin).
- `POST /usuarios/admin/usuarios/{id}/desactivar` — desactivar (admin).

### Productos
- `POST /productos/` — crear (auth requerida).
- `GET /productos/` — buscar/listar con filtros y paginación.
- `GET /productos/{id}` — ver uno.
- `PATCH /productos/{id}` — actualizar.
- `POST /productos/admin/{id}/descontinuar` — soft delete (admin).
- `POST /productos/admin/{id}/reactivar` — reactivar (admin).

### Health
- `GET /` — info básica.

---

## Formato de errores

Todas las excepciones devuelven:

```json
{
  "error": {
    "code": "duplicate_resource",
    "message": "El username 'juan' ya está en uso.",
    "request_id": "uuid-v4",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "extra": { ... }
  }
}
```

Códigos:
- `resource_not_found` (404)
- `duplicate_resource` (409)
- `business_rule_error` (400)
- `authentication_error` (401)
- `authorization_error` (403)
- `rate_limit_exceeded` (429)
- `validation_error` (422)
- `internal_server_error` (500)

---

## Middlewares

Orden de ejecución (request → response):

1. **RateLimitMiddleware** — corta requests abusivas (429).
2. **LoggingMiddleware** — loguea cada request con `request_id` (UUID v4).
3. **TimingMiddleware** — mide tiempo de procesamiento (header `X-Response-Time-ms`).
4. **CORSMiddleware** — agrega headers CORS.

Headers que agrega:
- `X-Request-ID` — UUID v4 único por request.
- `X-Response-Time-ms` — duración en ms.
- `Server-Timing` — header estándar W3C.
- `X-RateLimit-Limit` / `X-RateLimit-Remaining` — info del rate limit.
- `Retry-After` — segundos a esperar (solo en 429).

---

## Notas de diseño

- **Rate limiter en memoria**: el `TokenBucket` vive en el proceso. Para multi-worker (gunicorn con N workers) necesitarías Redis. La interfaz `RateLimiter` está pensada para que sea fácil de cambiar.
- **JWT en cookie HttpOnly**: más seguro contra XSS que `localStorage`. El frontend NO necesita hacer nada — el navegador envía la cookie automáticamente.
- **Soft delete**: usuarios y productos nunca se borran físicamente; se marcan como `is_active=False`. Esto preserva auditoría.
- **Schemas separados de Models**: el `UserPublic` no incluye `hashed_password`. El `UserCreate` acepta `password` (plaintext) pero el Service lo hashea antes de persistir.
- **Test database**: usamos SQLite in-memory con `StaticPool` para velocidad. Para CI con Postgres real, cambiar `TEST_DATABASE_URL` a `postgresql://...` y usar `NullPool` (ver cap12).
