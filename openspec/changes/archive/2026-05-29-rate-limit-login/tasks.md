## 1. Setup

- [x] 1.1 Agregar `slowapi` a `requirements.txt`
- [x] 1.2 Instalar dependencia (`pip install slowapi`)
- [x] 2.1 En `main.py`, importar `Limiter`, `_rate_limit_exceeded_handler` y `get_remote_address`
- [x] 2.2 Crear `limiter = Limiter(key_func=get_remote_address)` y asignarlo a `app.state.limiter`
- [x] 2.3 Agregar `app.add_exception_handler(429, _rate_limit_exceeded_handler)`
- [x] 3.1 En `Auth/router.py`, importar `limiter` desde `main` (o desde un módulo compartido)
- [x] 3.2 Agregar `@limiter.limit("5/minute")` al endpoint `POST /login`
- [x] 3.3 Agregar parámetro `request: Request` al handler de login (SlowAPI lo necesita para leer la IP)
- [x] 3.4 Verificar que la respuesta 429 incluye header `Retry-After`
- [x] 4.1 Probar: 5 logins fallidos seguidos → el 6to da 429
- [x] 4.2 Probar: esperar 1 minuto → el límite se reinicia
- [x] 4.3 Probar: login exitoso no se ve afectado por el límite
