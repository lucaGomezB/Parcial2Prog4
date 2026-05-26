# Guion de Presentación — Food Store API con Swagger UI y ReDoc

**Duración estimada:** 10-12 minutos  
**Formato:** Slides → Swagger UI / ReDoc → Código  
**Enfoque:** 100% API, sin frontend. Cada endpoint se muestra desde la documentación interactiva.

---

## Bloque 1 — Introducción (1:30)

### Slide 1 | Portada (0:15)

> **En pantalla:** Título "Food Store API — Documentación Interactiva con Swagger y ReDoc"
>
> **Narración:** "Vamos a recorrer la API completa de Food Store usando Swagger UI y ReDoc, las dos herramientas de documentación automática que genera FastAPI."

---

### Slide 2 | Swagger UI vs ReDoc (0:45)

> **En pantalla:** Split screen: izquierda Swagger UI (`/docs`), derecha ReDoc (`/redoc`).
>
> | Característica | Swagger UI | ReDoc |
> |---------------|-----------|-------|
> | Interactivo | ✅ Probar endpoints | ❌ Solo lectura |
> | Búsqueda | ❌ | ✅ |
> | Layout | Acordeón por endpoint | Scroll único por tag |
> | Ideal para | Desarrollo y debugging | Documentación para consumo |
>
> **Narración:** "FastAPI genera automáticamente ambas. Swagger UI permite ejecutar requests desde el navegador — ideal para desarrollo. ReDoc es más limpio y legible — ideal para documentación. Ambas se actualizan solas al cambiar el código."

---

### Slide 3 | Estructura de Tags (0:30)

> **En pantalla:** Swagger UI mostrando los tags expandidos:
> ```
> Auth, Usuarios, Roles, Direcciones de Entrega,
> Categorías, Productos, Ingredientes,
> Estados Pedido, Formas de Pago, Pedidos
> ```
>
> **Narración:** "La API está organizada en 10 tags que corresponden a los 3 módulos del backend. Cada tag agrupa los endpoints de un recurso."

---

## Bloque 2 — Autenticación (2:00)

### Slide 4 | Login — POST /auth/login (0:45)

> **En pantalla:** Swagger UI abierto en `POST /auth/login`. Cuerpo de ejemplo:
> ```json
> { "email": "admin@email.com", "password": "admin123" }
> ```
>
> **Narración:** "Vamos a ejecutar el login. Swagger UI nos permite escribir el body y probar. Al hacer clic en Execute, el backend valida contra bcrypt, genera un JWT de acceso y lo devuelve en la respuesta."
>
> **Demo (15s):** Click "Execute". Mostrar la respuesta 200 con `access_token` y `expires_in`. Mostrar también las cookies en los response headers.
>
> **Código (10s):** Mostrar `Auth/router.py` — el endpoint `login()` que llama al service y construye la respuesta.

---

### Slide 5 | Authorize — Autenticar en Swagger (0:30)

> **En pantalla:** Click en "Authorize" en Swagger UI, pegar el token JWT.
>
> **Narración:** "Swagger UI permite configurar el token globalmente con el botón Authorize. A partir de ahí, todos los endpoints protegidos envían el Bearer token automáticamente."
>
> **Demo (10s):** Copiar el token de la respuesta anterior, pegarlo en el modal Authorize, cerrar.

---

### Slide 6 | GET /auth/me — Usuario Actual (0:45)

> **En pantalla:** Swagger UI en `GET /auth/me`. Click Execute.
>
> **Narración:** "Con el token configurado, llamamos a `/auth/me`. Devuelve los datos del usuario autenticado incluyendo sus roles. Estos roles se usan para RBAC en todos los demás endpoints."
>
> **Demo (10s):** Execute, mostrar respuesta con `id`, `nombre`, `email`, `roles: ["ADMIN"]`.
>
> **Código (10s):** Mostrar `Auth/router.py` — `get_current_user` — cómo extrae y valida el JWT, busca el usuario en BD, y lo inyecta como dependencia.

---

## Bloque 3 — Catálogo de Productos (2:30)

### Slide 7 | Categorías — Árbol Jerárquico (0:45)

> **En pantalla:** ReDoc scrolleando el tag Categorías. Enfocar `GET /categorias/tree`.
>
> **Narración:** "Las categorías tienen estructura jerárquica padre-hijo. El endpoint tree devuelve el árbol completo con recursión infinita. Útil para menus de navegación."
>
> **Demo (10s):** Execute en Swagger, mostrar el JSON response con `subcategorias` anidadas.
>
> **Código (10s):** Mostrar `Categoria/models.py` — `parent_id` con FK autorreferenciante y `subcategorias: List[Categoria]`.

---

### Slide 8 | Productos — CRUD Completo (0:45)

> **En pantalla:** Swagger en `POST /productos/` con body de ejemplo:
> ```json
> { "nombre": "Hamburguesa Clásica", "precio_base": 75.00, ... }
> ```
>
> **Narración:** "El endpoint de productos acepta relaciones M:N con ingredientes y categorías en el mismo POST. Usa transacción atómica con Unit of Work."
>
> **Demo (10s):** Execute POST, mostrar 201 Created. Luego `GET /productos/` con paginación `?skip=0&limit=10`.
>
> **Código (10s):** Mostrar `CatalogoDeProductos/uow.py` — cómo agrupa los repositorios de Producto, Categoría e Ingrediente en una sola transacción.

---

### Slide 9 | Filtros y Paginación (0:30)

> **En pantalla:** Swagger mostrando los query params de `GET /productos/`: `skip`, `limit`.
>
> **Narración:** "Cada endpoint de listado soporta paginación con `skip` y `limit`. El backend usa `offset().limit()` de SQLAlchemy. El máximo de `limit` está acotado a 500 para evitar abusos."
>
> **Demo (10s):** Probar `GET /productos/?skip=0&limit=2` → 2 resultados. Cambiar a `skip=2` → página 2.

---

## Bloque 4 — Pedidos y Trazabilidad (2:30)

### Slide 10 | Crear Pedido — POST /pedidos/ (0:45)

> **En pantalla:** Swagger en `POST /pedidos/`. Body con `detalles` (snapshots de productos).
> ```json
> {
>   "forma_pago_codigo": "EFECTIVO",
>   "subtotal": 150.00,
>   "detalles": [{
>     "producto_id": 1, "cantidad": 2,
>     "nombre_snapshot": "Hamburguesa", "precio_snapshot": 75.00
>   }]
> }
> ```
>
> **Narración:** "Al crear un pedido, los detalles llevan snapshots de nombre y precio. Esto asegura que aunque el producto cambie en el futuro, el pedido conserva los datos originales."
>
> **Demo (15s):** Execute el POST. Mostrar respuesta 201 con `estado_codigo: "CONFIRMADO"`. Explicar que el parámetro `auto_confirmar=true` (default) avanza automáticamente de PENDIENTE a CONFIRMADO.
>
> **Código (10s):** Mostrar `Pedido/router.py` — el POST / con `auto_confirmar` y la llamada a `avanzar_estado()`.

---

### Slide 11 | FSM — Avanzar Estado (0:45)

> **En pantalla:** Swagger en `POST /pedidos/{id}/avanzar`. (Requiere ADMIN o PEDIDOS).
>
> **Narración:** "Los pedidos siguen una FSM: PENDIENTE → CONFIRMADO → EN_PREP → EN_CAMINO → ENTREGADO. Cada transición se registra en HistorialEstadoPedido (INSERT-only). Endpoints protegidos con rol ADMIN o PEDIDOS."
>
> **Demo (10s):** Execute avanzar. Mostrar respuesta con `estado_anterior` y `estado_actual`.
>
> **Código (10s):** Mostrar `Pedido/service.py` — `TRANSICIONES_VALIDAS` y el método `avanzar_estado()` — cómo valida, registra en historial, y actualiza.

---

### Slide 12 | Historial y Filtros (0:30)

> **En pantalla:** Swagger mostrando `GET /pedidos/activos` y `GET /pedidos/historial`.
>
> **Narración:** "Dos endpoints complementarios: activos devuelve los que NO están en estado terminal; historial devuelve solo ENTREGADO y CANCELADO. Ambos soportan filtro por usuario autenticado."
>
> **Demo (10s):** Ejecutar ambos endpoints y comparar las respuestas.

---

### Slide 13 | Trazabilidad — HistorialEstadoPedido (0:30)

> **En pantalla:** ReDoc mostrando el schema `HistorialEstadoPedido`.
>
> **Narración:** "Cada cambio de estado queda registrado en una tabla INSERT-only: quién lo hizo, desde qué estado, hacia qué estado, y cuándo. Esto da trazabilidad completa del pedido."
>
> **Código (10s):** Mostrar `HistorialEstadoPedido/models.py` — los campos `pedido_id`, `estado_desde`, `estado_hacia`, `usuario_id`, `created_at`.

---

## Bloque 5 — Seguridad y Roles (1:30)

### Slide 14 | RBAC — require_roles (0:45)

> **En pantalla:** Swagger mostrando un endpoint protegido como `DELETE /productos/{id}`. Sin autorización devuelve 401. Con token pero sin rol devuelve 403.
>
> **Narración:** "La protección es de dos capas: `get_current_user` verifica el JWT (401 si falta o expiró). `require_roles` verifica que el usuario tenga al menos uno de los roles necesarios (403 si no)."
>
> **Demo (15s):** Sin token → Execute DELETE → 401. Con token de CLIENT → 403. Con token de ADMIN → 204 Success.
>
> **Código (10s):** Mostrar `Auth/dependencies.py` — `require_roles()` — la función factory que compara roles y lanza 403.

---

### Slide 15 | Soft Delete (0:45)

> **En pantalla:** Swagger mostrando `DELETE /usuarios/{id}` (soft-delete). Luego `GET /usuarios/` y el usuario ya no aparece.
>
> **Narración:** "Los DELETE no borran físicamente, marcan `deleted_at`. El `BaseRepository` filtra automáticamente `WHERE deleted_at IS NULL` en todos los queries. Si necesitamos recuperar datos, están en la BD."
>
> **Código (10s):** Mostrar `models/base.py` — `SoftDeleteModel` con `deleted_at` y `BaseRepository.get_all()` con el filtro condicional.

---

## Bloque 6 — Documentación Automática (1:00)

### Slide 16 | OpenAPI Schema (0:30)

> **En pantalla:** Navegar a `/openapi.json`. Mostrar el JSON enorme con todos los schemas y endpoints.
>
> **Narración:** "FastAPI genera automáticamente un archivo OpenAPI 3.0 en `/openapi.json`. Swagger UI y ReDoc lo consumen. Podemos importarlo en herramientas como Postman o generar clients automáticos."
>
> **Demo (10s):** Mostrar el JSON en el navegador, buscar un schema específico (ej: "PedidoCreate").

---

### Slide 17 | Cierre — Demo Rápida (0:30)

> **En pantalla:** Recorrido rápido por Swagger UI ejecutando endpoints clave:
> 1. POST /auth/login → obtener token
> 2. Authorize → pegar token
> 3. GET /productos/ → listar productos
> 4. POST /pedidos/ → crear pedido
> 5. POST /pedidos/{id}/avanzar → avanzar estado
>
> **Narración:** "En menos de 30 segundos ejecutamos el flujo completo: autenticación, consulta de productos, creación de pedido y avance de estado. Todo desde la documentación interactiva."

---

## Notas para el presentador

- **Swagger vs ReDoc:** Usá Swagger para las demos interactivas (ejecutar endpoints). Usá ReDoc para mostrar la estructura general (schemas, tags).
- **Token:** Después del login, acordate de hacer clic en "Authorize" y pegar el token. Sin eso, los endpoints protegidos devuelven 401 y la demo se traba.
- **Datos de prueba:** Usá `admin@email.com / admin123` como usuario ADMIN para mostrar todos los endpoints.
- **Errores:** Si un endpoint devuelve 422, mostrá el error en pantalla y explicá que es la validación de Pydantic — es una feature, no un bug.
- **Flujo alternativo:** Si Swagger UI está lento, tené ReDoc abierto como backup para mostrar la documentación mientras cargan los endpoints.
