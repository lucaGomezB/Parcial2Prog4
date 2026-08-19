# Guion de Presentación — Food Store E-commerce

**Duración estimada:** 13-15 minutos  
**Formato:** Slides → Código backend → Demo frontend (como consumidor)  
**Protagonista:** Backend FastAPI. El frontend muestra lo que el backend expone.

---

## Bloque 1 — Arquitectura (2:00)

### Slide 1 | Portada (0:15)

> **En pantalla:** Título "Food Store API — Backend FastAPI + Frontend React"
>
> **Narración:** "Aplicación e-commerce con backend en Python FastAPI organizado en 3 módulos, base de datos PostgreSQL, y frontend React que consume la API."

---

### Slide 2 | Arquitectura General (0:45)

> **En pantalla:** Diagrama de capas:
> ```
> PostgreSQL ← SQLModel ORM ← FastAPI ← HTTP/REST ← (Proxy Vite) ← React
>                                    ↑
>                             3 Módulos:
>                         IdentidadYAcceso
>                         CatalogoDeProductos
>                         VentasPagosTrazabilidad
> ```
>
> **Narración:** "El backend es el núcleo. FastAPI recibe requests HTTP, SQLModel mapea a PostgreSQL. El frontend React es solo un consumidor más de la API — podríamos tener una app móvil o Postman haciendo las mismas llamadas."
>
> **Código (10s):** Mostrar `main.py` — los 10 `app.include_router(...)` que registran todos los módulos.

---

### Slide 3 | Organización de Módulos — Patrón por Capas (1:00)

> **En pantalla:** Árbol de un submódulo genérico:
> ```
> modules/<Area>/<Recurso>/
> ├── models.py      ← SQLModel: tabla + relaciones
> ├── schemas.py     ← Pydantic: validación entrada/salida
> ├── repository.py  ← BaseRepository<T>: consultas SQL
> ├── service.py     ← Lógica de negocio
> ├── router.py      ← Endpoints HTTP
> └── ...
> ```
>
> **Narración:** "Cada recurso del backend sigue este patrón en 5 capas. El Router expone los endpoints. El Service tiene la lógica de negocio. El Repository encapsula las consultas. El Model define la tabla SQL. El Schema es el contrato Pydantic. Las transacciones se manejan con Unit of Work."
>
> **Código (15s):** Mostrar `VentasPagosTrazabilidad/uow.py` — `__enter__/__exit__`, `commit()`, `rollback()`. Explicar: "Si algo falla, todo se deshace atómicamente."

---

## Bloque 2 — Autenticación y Seguridad — Módulo IdentidadYAcceso (3:00)

### Slide 4 | Login: POST /auth/login (1:00)

> **En pantalla:** Diagrama de flujo desde el endpoint:
> ```
> POST /auth/login { email, password }
>   → Service valida bcrypt
>   → Genera JWT access_token (30 min)
>   → Genera refresh_token (7 días) y lo guarda en httpOnly cookie
>   → Responde { access_token, expires_in }
> ```
>
> **Narración:** "El endpoint `POST /auth/login` recibe email y password. El servicio usa bcrypt para verificar el hash. Si coincide, genera dos tokens: un JWT de acceso corto que vuelve en el body, y un refresh token de larga duración que se setea como cookie httpOnly — el frontend nunca toca ese refresh token."
>
> **Código backend (15s):** Mostrar `Auth/router.py` — el endpoint `login()`. Señalar: cómo llama al service, cómo construye la respuesta con `set_cookie()` para el refresh_token.
>
> **Demo frontend (10s):** Mostrar el formulario de login. Hack: abrir DevTools > Application > Cookies y mostrar que la cookie httpOnly NO aparece (porque httpOnly no se ve desde JavaScript). Mostrar localStorage con el access_token.

---

### Slide 5 | JWT + Refresh Automático — Axios Interceptor (1:00)

> **En pantalla:** Diagrama del interceptor de Axios:
> ```
> Response 401 → ¿Es refresh? → Sí → /login
>                    → No → ¿Ya retry? → Sí → reject
>                          → No → POST /auth/refresh (cookie)
>                                → ¿OK? → nuevo token → retry
>                                → No → /login
> ```
>
> **Narración:** "Cuando el access_token expira, el backend responde 401. El interceptor de Axios atrapa ese error, llama a `/auth/refresh` — el refresh_token viaja solo en la cookie httpOnly. Si funciona, guarda el nuevo access_token y reintenta la request original. Si falla, redirige al login. Todo transparente para el usuario."
>
> **Código backend (10s):** Mostrar `Auth/router.py` — `POST /auth/refresh` — cómo extrae el refresh_token de la cookie, valida en BD, y genera un nuevo par de tokens.
>
> **Código frontend (10s):** Mostrar `client.ts` — el response interceptor con `failedQueue`, `isRefreshing`, `processQueue`.

---

### Slide 6 | RBAC: require_roles + Modelo Usuario-Rol (1:00)

> **En pantalla:** Diagrama entidad-relación:
> ```
> Usuario ──── usuario_rol ──── Rol
>   id           usuario_id      codigo (PK): ADMIN, STOCK, PEDIDOS, CLIENT
>   email        rol_codigo      nombre
>   password_hash                descripcion
> ```
>
> **Narración:** "Cada usuario tiene roles mediante una tabla M:N `usuario_rol`. El backend protege los endpoints con `require_roles(['ADMIN'])` — un dependency checker de FastAPI que valida que el usuario tenga al menos uno de los roles requeridos. Si no, responde 403."
>
> **Código backend (15s):** Mostrar `Auth/dependencies.py` — `require_roles()` — la función factory. Explicar: "Devuelve una dependencia de FastAPI que se inyecta en los endpoints para verificar roles antes de ejecutar cualquier lógica."
>
> **Código backend (10s):** Mostrar `usuario_rol.py` — el modelo `UsuarioRol` con el `UniqueConstraint("usuario_id", "rol_codigo")`.
>
> **Demo frontend (10s):** Mostrar en pantalla: loguearse como CLIENT → intentar entrar a `/admin/usuarios` → redirige a productos. Loguearse como ADMIN → sí entra.

---

## Bloque 3 — Módulo Catálogo de Productos (2:30)

### Slide 7 | Categorías Jerárquicas — Self-referencing FK (0:45)

> **En pantalla:** Árbol visual:
> ```
> Bebidas (parent_id = NULL)
> ├── Bebidas Frías (parent_id = Bebidas.id)
> │   └── ... (parent_id = BebidasFrías.id)
> └── Bebidas Calientes
> ```
>
> **Narración:** "Las categorías usan una FK autorreferenciante: `parent_id` apunta a `categoria.id`. NULL significa categoría raíz. El endpoint `GET /categorias/tree` construye el árbol con una relación recursiva de SQLAlchemy — el frontend lo recibe como JSON anidado y lo renderiza con un componente recursivo."
>
> **Código backend (15s):** Mostrar `Categoria/models.py` — `parent_id: Optional[int] = Field(foreign_key="categoria.id")` y la relación `subcategorias: List[Categoria]` con `remote_side`.
>
> **Código frontend (10s):** Mostrar `CategoryTreeRow` — el componente que se llama a sí mismo para renderizar subcategorías.
>
> **Demo (10s):** Mostrar la página de categorías, expandir/colapsar el árbol.

---

### Slide 8 | Productos + Ingredientes — Relaciones M:N (0:45)

> **En pantalla:** Diagrama entidad-relación:
> ```
> Producto ── producto_ingrediente ── Ingrediente
>   id          producto_id            id
>   nombre      ingrediente_id        nombre
>   precio_base                        es_alergeno
>   stock_cantidad
> ```
>
> **Narración:** "Productos e Ingredientes se relacionan M:N mediante tablas puente. Un Producto puede tener múltiples Ingredientes; un Ingrediente puede estar en múltiples Productos. El endpoint `POST /productos/` acepta crear un producto con sus ingredientes y categorías en una sola request, todo dentro de una misma transacción."
>
> **Código backend (15s):** Mostrar `CatalogoDeProductos/uow.py` — cómo agrupa los repositorios. Mostrar `Producto/service.py` — el create que recibe ingredientes y categorías en el mismo payload.

---

### Slide 9 | Paginación y Filtros — Query Params (0:30)

> **En pantalla:** Swagger UI mostrando `GET /productos/?skip=0&limit=10`.
>
> **Narración:** "Todos los endpoints de listado soportan `skip` y `limit` para paginación. El `BaseRepository.get_all()` usa `offset().limit()` de SQLAlchemy con límite máximo de 500. Los filtros adicionales van como query params opcionales."
>
> **Código backend (10s):** Mostrar `base_repository.py` — `get_all()` con `offset`, `limit`, `order_by`, y el filtro automático `WHERE deleted_at IS NULL` para soft-delete.

---

### Slide 10 | Soft Delete — deleted_at (0:30)

> **En pantalla:** Modelo `SoftDeleteModel`:
> ```python
> class SoftDeleteModel(TimestampModel):
>     deleted_at: Optional[datetime] = Field(default=None)
> ```
>
> **Narración:** "Ningún DELETE borra físicamente. Heredan de `SoftDeleteModel` que agrega `deleted_at`. El `BaseRepository` filtra automáticamente `WHERE deleted_at IS NULL` en todos los queries. Si necesitamos recuperar datos, están en la BD."
>
> **Código backend (10s):** Mostrar `base_repository.py` — el `if self._is_soft_delete:` en `get_all()` y `get_by_id()`.

---

## Bloque 4 — Módulo Ventas, Pagos y Trazabilidad (3:00)

### Slide 11 | Pedidos — Modelo y Schemas (0:45)

> **En pantalla:** Schema `PedidoCreate` de Pydantic:
> ```python
> class PedidoCreate(BaseModel):
>     usuario_id: Optional[int] = None  # ← backend auto-asigna
>     direccion_id: Optional[int] = None
>     forma_pago_codigo: str
>     subtotal: Decimal
>     detalles: Optional[List[DetallePedidoInput]]
> ```
>
> **Narración:** "El schema de creación de pedidos usa Pydantic con validación automática. Los `Decimal` aseguran precisión monetaria. `usuario_id` es opcional porque el router lo auto-asigna del token — el frontend nunca decide quién es el dueño del pedido."
>
> **Código backend (15s):** Mostrar `Pedido/schemas.py` — `PedidoCreate`, `DetallePedidoInput` con `precio_snapshot: Decimal`. Explicar: "Los snapshots de nombre y precio congelan el valor al momento de la compra."

---

### Slide 12 | FSM — Máquina de Estados Finitos (1:00)

> **En pantalla:** Diagrama de la FSM:
> ```
> PENDIENTE → CONFIRMADO → EN_PREP → EN_CAMINO → ENTREGADO
>     ↓            ↓          ↓           ↓
>     └────────────┴──────────┴───────────┘──→ CANCELADO
> ```
>
> **Narración:** "Los pedidos siguen una Máquina de Estados Finitos definida en `TRANSICIONES_VALIDAS`. Cada transición se registra en `HistorialEstadoPedido` (INSERT-only, sin UPDATE ni DELETE). El método `avanzar_estado()` valida la transición, registra en historial, y actualiza el estado."
>
> **Código backend (15s):** Mostrar `Pedido/service.py` — `TRANSICIONES_VALIDAS` y el método `avanzar_estado()`. Señalar: cómo levanta 400 si el estado es terminal, cómo registra en `HistorialEstadoPedido`, cómo actualiza.
>
> **Código frontend (10s):** Mostrar `PedidosPage.tsx` — los tabs Activos/Historial consumiendo `GET /pedidos/activos` y `GET /pedidos/historial`.
>
> **Demo (10s):** Como ADMIN, avanzar un pedido de PENDIENTE a CONFIRMADO. Mostrar cómo cambia el badge de color.

---

### Slide 13 | Auto-select de Dirección Principal (0:45)

> **En pantalla:** Código del auto-select en `PedidoService.create()`:
> ```python
> if data.direccion_id is None:
>     principal = direccion_repo.get_principal(data.usuario_id)
>     if principal:
>         data.direccion_id = principal.id
> ```
>
> **Narración:** "Cuando se crea un pedido sin `direccion_id`, el backend busca automáticamente la dirección principal del usuario. Si existe, la asigna. Si no, `costo_envio` se setea a 0. Toda esta lógica está en el service, no en el router ni en el frontend."
>
> **Código backend (10s):** Mostrar `DireccionEntrega/service.py` — `set_principal()` — cómo desmarca la anterior y marca la nueva en una transacción. Explicar: "Solo una dirección principal a la vez, manejado en la capa de aplicación."
>
> **Demo frontend (10s):** Mostrar DireccionesPage, crear una dirección, marcarla como principal. Ir al carrito, ver que está preseleccionada.

---

### Slide 14 | Endpoints REST de Pedidos (0:30)

> **En pantalla:** Tabla de endpoints del tag Pedidos:
>
> | Método | Path | Auth | 
> |--------|------|------|
> | GET | `/pedidos/` | ADMIN, PEDIDOS |
> | GET | `/pedidos/activos` | Autenticado |
> | GET | `/pedidos/mis-pedidos` | Autenticado |
> | GET | `/pedidos/historial` | Autenticado |
> | POST | `/pedidos/` | Autenticado |
> | POST | `/pedidos/{id}/avanzar` | ADMIN, PEDIDOS |
> | POST | `/pedidos/{id}/cancelar` | Autenticado (owner-scoped) |
>
> **Narración:** "Cada endpoint tiene su nivel de acceso. `GET /pedidos/` solo ADMIN/PEDIDOS. `POST /pedidos/{id}/cancelar` owner-scoped: un CLIENT solo cancela sus propios pedidos. El router delega en el service, que delega en el repository, todo dentro de una UoW."

---

## Bloque 5 — Patrones de Diseño Backend (2:00)

### Slide 15 | BaseRepository — Genérico Tipado (0:45)

> **En pantalla:** 
> ```python
> T = TypeVar("T", bound=SQLModel)
> 
> class BaseRepository(Generic[T]):
>     def get_all(self, skip=0, limit=100) -> List[T]: ...
>     def get_by_id(self, entity_id) -> Optional[T]: ...
>     def add(self, entity: T) -> T: ...
> ```
>
> **Narración:** "`BaseRepository` es genérico: recibe el tipo del modelo (`T`) y provee CRUD base. Los repositorios específicos heredan y agregan métodos custom. `UsuarioRepository` agrega `get_by_email()`. El filtro soft-delete es automático — no hay que acordarse."
>
> **Código (15s):** Mostrar `base_repository.py` — `get_all()` con `offset`, `limit`, `order_by`, y el `if self._is_soft_delete:`.

---

### Slide 16 | Unit of Work — Transacciones Atómicas (0:45)

> **En pantalla:**
> ```python
> class VentasPagosTrazabilidadUnitOfWork:
>     def __enter__(self): return self
>     def __exit__(self, exc_type, exc, tb):
>         if exc_type: self.rollback()
>         else: self.commit()
>         return False
> ```
>
> **Narración:** "Cada módulo tiene su Unit of Work que agrupa todos los repositorios del módulo. Si cualquier operación dentro del `with` falla, el `__exit__` detecta la excepción y hace rollback. Todo o nada."
>
> **Código backend (10s):** Mostrar `uow.py` de VentasPagosTrazabilidad — los repositorios que contiene. Mostrar cómo se usa en el service: `with VentasPagosTrazabilidadUnitOfWork(session) as uow:`.

---

### Slide 17 | Pydantic Schemas — Validación Automática (0:30)

> **En pantalla:**
> ```python
> class PedidoCreate(BaseModel):
>     subtotal: Decimal
>     costo_envio: Decimal = Decimal('50.00')
>     
>     @model_validator(mode="after")
>     def validate_total(self):
>         if self.subtotal - self.descuento + self.costo_envio < 0:
>             raise ValueError("Total negativo")
> ```
>
> **Narración:** "Pydantic valida tipos, convierte automáticamente (int→Decimal), y ejecuta validadores custom. Si algo no cumple, FastAPI responde 422 con el detalle del error. Sin necesidad de if/else en el router."
>
> **Código (10s):** Mostrar `Pedido/schemas.py` — `model_validator` y `field_validator`.

---

## Bloque 6 — Frontend como Consumidor (2:00)

### Slide 18 | apiFetch y Tipos — Cómo el Frontend Llama al Backend (0:45)

> **En pantalla:**
> ```typescript
> // Frontend: define el tipo que espera
> export interface Pedido { id: number; estado_codigo: string; ... }
> 
> // Frontend: llama al endpoint (el backend valida)
> export const pedidosApi = {
>   getActivos: () => apiFetch<Pedido[]>("/pedidos/activos"),
>   create: (data) => apiFetch<Pedido>("/pedidos/", { method: "POST", body: ... }),
> };
> ```
>
> **Narración:** "El frontend define interfaces TypeScript que reflejan los schemas del backend. `apiFetch` envuelve a Axios y tipa la respuesta. Si el backend cambia el schema, TypeScript no compila — detección de errores en build, no en runtime."
>
> **Código frontend (10s):** Mostrar `api/pedidos.ts` — las interfaces y los métodos. Mostrar `client.ts` — `apiFetch()` que parsea el body y lo envía con axios.

---

### Slide 19 | React Router — Consumiendo Endpoints Protegidos (0:45)

> **En pantalla:** Tabla rutas → endpoints → roles:
> ```
> /productos      → GET  /productos/       → Cualquiera
> /pedidos        → GET  /pedidos/activos   → Autenticado
> /admin/usuarios → GET  /usuarios/         → ADMIN
> /categorias     → GET  /categorias/tree   → ADMIN, PEDIDOS
> ```
>
> **Narración:** "Las rutas del frontend reflejan los endpoints del backend. La protección es doble: el frontend oculta las rutas que el usuario no puede ver (UX), y el backend las protege con `require_roles` (seguridad). Si alguien modifica el frontend, el backend igual lo frena."
>
> **Código frontend (10s):** Mostrar `App.tsx` — las condiciones `{canSeeFullNav && <Route...>}` que espejan los permisos del backend.
>
> **Demo (10s):** Como CLIENT, mostrar que no aparece "Usuarios" en el navbar. Como ADMIN, sí aparece.

---

### Slide 20 | Resumen: Backend como Fuente de Verdad (0:30)

> **En pantalla:** Diagrama final:
> ```
> [Base de Datos] ← [SQLModel ORM]
>                       ↑
>                 [Service Layer]  ← reglas de negocio
>                       ↑
>                 [REST API]      ← contratos Pydantic
>                       ↑
>                 [HTTP/JSON]     ← cualquier cliente
>                       ↑
>              ┌────────┴────────┐
>           [React]          [Swagger UI]
> ```
>
> **Narración:** "Todo arranca en la base de datos y sube hasta el cliente. La API REST es el contrato — cualquier cliente (React, mobile, Postman) la consume igual. El frontend es solo una de las caras de la API. El backend es el que tiene las reglas de negocio, las validaciones, y la seguridad."

---

## Notas para el presentador

- **Ritmo:** ~45s por slide. Cuando muestres código backend, NO leas línea por línea — señalá la estructura y explicá el propósito.
- **Demo frontend:** El frontend es el "escaparate" del backend. Mostralo para que se vea cómo se consume la API, no para explicar React.
- **Swagger como respaldo:** Si la demo del frontend falla, abrí Swagger UI en `/docs` y mostrá los endpoints directamente.
- **Preparación:** Dejá logueado un ADMIN antes de la presentación. Tené Swagger UI abierto en otra pestaña como backup.
- **Tiempo:** 20 slides × ~45s = 15 minutos. Si ves que te excedés, acortá las demos del frontend — lo importante es el backend.
