# Guion de Presentacion — Food Store E-commerce (Version Final)

**Duracion estimada:** 14-15 minutos
**Formato:** Slides → Codigo backend → Demo frontend
**Protagonista:** Backend FastAPI. El frontend muestra lo que el backend expone.

---

## Bloque 1 — Arquitectura y Nucleo (3:00)

### Slide 1 | Portada (0:15)

> **En pantalla:** Titulo "Food Store API — Backend FastAPI + Frontend React" con nombres de los integrantes.
>
> **Narracion:** "Aplicacion e-commerce con backend Python FastAPI, PostgreSQL, y frontend React. Recorremos todo en orden: arquitectura, autenticacion, catalogo, pedidos, WebSockets, MercadoPago, Cloudinary, estadisticas, tests y frontend."

---

### Slide 2 | Arquitectura General + Patrones (1:30)

> **En pantalla:** Diagrama de capas + UoW + BaseRepository:
> ```
> PostgreSQL ← SQLModel ← FastAPI ← React (Vite)
>                   ↑
>            3 Bounded Contexts:
>        IdentidadYAcceso, CatalogoDeProductos, VentasPagosTrazabilidad
> 
> Router → Service → UnitOfWork → Repository → Model
> ```
> ```python
> # UoW — transaccion atomica
> class VentasPagosTrazabilidadUnitOfWork:
>     def __exit__(self, exc_type, exc, tb):
>         if exc_type: self.rollback(); return False
>         self.commit()
> 
> # BaseRepository<T> — CRUD generico con soft-delete automatico
> class BaseRepository(Generic[T]):
>     def get_all(self, skip=0, limit=100) -> List[T]: ...
> ```
>
> **Narracion:** "El backend es el nucleo. Tres bounded contexts independientes. Cada recurso sigue 5 capas. UnitOfWork maneja transacciones atomicas: si algo falla, todo se deshace. BaseRepository generico provee CRUD, paginacion y soft delete automatico — nunca borramos fisicamente, solo marcamos deleted_at."
>
> **Codigo backend (20s):** Mostrar `main.py` con los `include_router`. Mostrar `uow.py` — `__enter__/__exit__`. Mostrar `base_repository.py` — clase generica.

---

### Slide 3 | Core + Alembic + Seed (0:45)

> **En pantalla:** Arbol `core/` + 11 migraciones:
> ```
> core/
> ├── database.py, security/ (JWT + bcrypt)
> ├── websocket_manager.py, rate_limit.py
> ├── problem_response.py (RFC 7807), cloudinary_config.py
>
> migrations/versions/ → 11 archivos
> seed.py → idempotente (get_or_create)
> ```
>
> **Narracion:** "El directorio core/ contiene infraestructura compartida. Alembic para 11 migraciones versionadas. Seed idempotente: roles, estados y admin no se duplican. Soft delete en todos los modelos: deleted_at, nunca DELETE fisico."
>
> **Codigo backend (15s):** Mostrar `database.py`, `seed.py` patron `get_or_create()`, `models/base.py` SoftDeleteModel.

---

## Bloque 2 — IdentidadYAcceso (2:00)

### Slide 4 | Auth — JWT + Refresh + RBAC (1:15)

> **En pantalla:** Diagrama login + RBAC:
> ```
> POST /auth/login → bcrypt → JWT (30min) + refresh cookie httpOnly (7d)
> POST /auth/refresh → rota tokens (revoca anterior)
> POST /auth/logout → revoca + limpia cookie
> 
> Usuario ── usuario_rol ── Rol (M:N)
> require_roles(['ADMIN']) → 401 sin token, 403 sin rol
> ```
>
> **Narracion:** "Login usa bcrypt, genera JWT de acceso en el body y refresh token en cookie httpOnly. El refresh rota: cada uso revoca el anterior. RBAC con tabla M:N usuario_rol y UniqueConstraint. require_roles distingue 401 (no autenticado) de 403 (sin permiso). Registro fuerza rol CLIENT — el frontend nunca decide roles."
>
> **Codigo backend (15s):** Mostrar `Auth/router.py` login/refresh/logout. Mostrar `dependencies.py` get_current_user + require_roles.
>
> **Demo (10s):** CLIENT → navbar sin "Usuarios". ADMIN → todo visible.

---

### Slide 5 | Usuario, Rol, Direcciones (0:45)

> **En pantalla:** Swagger tags Usuarios, Roles, Direcciones.
>
> **Narracion:** "CRUD de usuarios con soft delete, roles solo ADMIN, direcciones con el concepto de principal — solo una por usuario. `set_principal()` desmarca la anterior y marca la nueva en una transaccion atomica."
>
> **Codigo backend (10s):** Mostrar `DireccionEntrega/service.py` — set_principal() atomico.
>
> **Demo (10s):** Swagger: crear direccion, marcar principal, verificar que es la unica.

---

## Bloque 3 — Catalogo de Productos (1:30)

### Slide 6 | Categorias Jerarquicas + Productos M:N (1:30)

> **En pantalla:** Arbol categorias + diagrama M:N + Swagger:
> ```
> Bebidas (parent_id = NULL)
> ├── Frias (parent_id = Bebidas.id)
> └── Calientes
> 
> Producto ── producto_ingrediente ── Ingrediente
> ```
>
> **Narracion:** "Categorias con FK autorreferenciante — el endpoint /tree construye el arbol recursivo. Productos e Ingredientes M:N. POST /productos/ acepta crear producto con categorias e ingredientes en una sola request atomica. Paginacion con skip/limit, maximo 500. Soft delete: DELETE /productos/{id} marca deleted_at, el producto desaparece de listados pero los datos se preservan. El frontend renderiza categorias con componente recursivo y muestra productos con filtro por categoria, busqueda y skeleton loaders."
>
> **Codigo backend (15s):** Mostrar `Categoria/models.py` — parent_id + subcategorias. Mostrar Producto service — create con categorias e ingredientes.
>
> **Codigo frontend (10s):** Mostrar `CategoryTreeRow.tsx`, ProductosCliente con chips de categoria.

---

## Bloque 4 — Ventas, Pagos y Trazabilidad (3:00)

### Slide 7 | Pedidos — Máquina de Estados Finitos (FSM), Snapshots y Cancelacion (1:15)

> **En pantalla:** Diagrama Máquina de Estados Finitos (FSM):
> ```
> PENDIENTE → CONFIRMADO → EN_PREP → ENTREGADO (terminal)
>     ↓            ↓           ↓
>     └────────────┴───────────┘──→ CANCELADO (terminal)
> ```
>
> **Narracion:** "Máquina de Estados Finitos (FSM) de 5 estados, dos terminales. Cada transicion registrada en HistorialEstadoPedido — INSERT-only. Detalles capturan nombre_snapshot y precio_snapshot: aunque el producto cambie, el pedido conserva los valores del momento. Cancelacion requiere motivo, desde EN_PREP tambien se puede cancelar con restore de stock. Timeline en tiempo real visible en el popup de detalles."
>
> **Codigo backend (15s):** Mostrar `Pedido/service.py` — TRANSICIONES_VALIDAS, avanzar_estado(), _registrar_transicion(). Mostrar DetallePedido/models.py — snapshots.
>
> **Demo (10s):** Swagger: crear pedido → avanzar → cancelar con motivo → ver historial.

---

### Slide 8 | MercadoPago — Preferencia, Webhook, Redirect (1:45)

> **En pantalla:** Diagrama flujo MP:
> ```
> Frontend → POST /pagos/crear → Backend crea preferencia (idempotency_key UUID)
>   → Usuario paga en MP
>   → MP notifica Webhook IPN → Backend verifica (responde 200 OK siempre)
>   → MP redirige → Backend consulta API de MP (nunca confia en URL de retorno)
>   → Backend avanza pedido + notifica WS
> ```
>
> **Narracion:** "Tres patas: crear preferencia con idempotency_key UUID, webhook IPN que siempre responde 200, y redirect que consulta la API de MP para verificar. El backend NUNCA confia en la URL de retorno. La tabla Pago guarda mp_status, mp_status_detail, transaction_amount en Decimal. ACLARACION: no pudimos probar el flujo completo por un error en la integracion. La arquitectura esta correcta: backend orquesta, MP decide, pedido refleja la verdad. El codigo esta documentado y los tests unitarios cubren la logica."
>
> **Codigo backend (15s):** Mostrar `Pago/service.py` — init_mp_payment() con idempotency_key, process_webhook() con fetch a MP API.
>
> **Codigo frontend (10s):** Mostrar Carrito.tsx — flujo de pago: crear pedido → initPayment → redirect a MP.

---

## Bloque 5 — WebSockets + Cloudinary + Estadisticas (2:00)

### Slide 9 | WebSockets — ConnectionManager + Rooms (1:00)

> **En pantalla:** Diagrama WS:
> ```
> ConnectionManager
> ├── rooms: {"role:cocina" → {ws1,ws2}, "order:42" → {ws4}}
> └── socket_rooms: {ws1 → {"role:cocina"}} (mapa inverso)
> 
> Endpoints: /ws/pedidos/{id} (cliente), /ws/admin/pedidos (staff)
> JWT en query param, RBAC al conectar, broadcast sin duplicados
> ```
>
> **Narracion:** "WebSockets para tiempo real. ConnectionManager con doble mapa inverso para limpieza O(1). JWT en handshake, RBAC al conectar. Rooms por rol y por entidad. Broadcast evita duplicados. Frontend: useEstadoPedidoWS con backoff exponencial, badge de notificaciones en navbar, timeline que se refresca con eventos WS. Broadcast siempre DESPUES del commit UoW."
>
> **Codigo backend (15s):** Mostrar `websocket_manager.py` — connect/disconnect/broadcast.
>
> **Codigo frontend (10s):** Mostrar useEstadoPedidoWS.ts — backoff, wsStore, badge.

---

### Slide 10 | Cloudinary + Estadisticas (1:00)

> **En pantalla:** Swagger uploads + dashboard con graficos.
>
> **Narracion:** "Cloudinary: upload con validacion MIME (jpeg/png/gif/webp, 10MB max), delete por public_id solo ADMIN. Frontend con ImageCarousel aplicando transformaciones f_auto,q_auto,c_fill. Estadisticas: 5 endpoints ADMIN-only, Decimal para dinero, CANCELADO excluido, subtotal_snap para ingresos por producto, mp_status='approved' para ingresos confirmados, PAGO_LOCAL incluido. Frontend: 4 graficos Recharts con refetch automatico cada 60s y 4 tarjetas KPI."
>
> **Codigo backend (10s):** Mostrar `Uploads/service.py` — validacion + upload. Mostrar `Estadisticas/repository.py` — query con filtro CANCELADO + mp_status.
>
> **Demo (10s):** Dashboard con KPIs y graficos. Producto con imagenes Cloudinary.

---

## Bloque 6 — Tests + Frontend (2:30)

### Slide 11 | 155 Tests — Infraestructura y Cobertura (1:00)

> **En pantalla:** Arbol tests + tabla cobertura:
> ```
> Backend/tests/
> ├── conftest.py (SQLite, fixtures, factories, auth helpers)
> ├── test_identidad_acceso.py (38 tests)
> ├── test_pedidos.py (18 tests)
> ├── test_estadisticas.py (30 tests)
> ├── test_websocket.py (9 tests)
> └── ... (9 archivos, 155 tests total)
> ```
>
> **Narracion:** "155 tests: integracion con TestClient + SQLite en memoria, unitarios con MagicMock para APIs externas. conftest.py tiene fixtures reutilizables, helpers JWT, factories. Cobertura >60%. Cada modulo tiene 5+ tests. Los tests de Pedidos cubren toda la Máquina de Estados Finitos (FSM). Los de Auth validan register, login, RBAC. WebSocket tiene 9 tests de conexion, auth y desconexion."
>
> **Codigo backend (15s):** Mostrar `conftest.py` — engine, db_session, client, _create_auth_headers. Terminal con `pytest -v`.

---

### Slide 12 | Frontend — Feature Sliced + TanStack Query (1:30)

> **En pantalla:** Arbol FSD + query keys:
> ```
> src/
> ├── app/ (router, App shell)
> ├── features/ (auth, productos, pedidos, categorias, estadisticas)
> └── shared/ (api, components, hooks, store, utils)
> 
> TanStack Query: useQuery/useMutation, queryKeys descriptivos
> 5 stores Zustand tipados, selectores por slice, persistencia
> ```
>
> **Narracion:** "Frontend feature-sliced: cada feature autocontenida, imports Pages→Hooks→API→Types. Shared solo para codigo usado por 2+ features. Migramos de useEffect manual a TanStack Query: useQuery para GETs, useMutation para POST/PATCH/DELETE con invalidacion automatica. 5 stores Zustand tipados con selectores por slice. Diseno consistente con Tailwind, componentes compartidos (Toast, Modal, Skeleton), mobile-first con hamburger menu, badge WS en navbar."
>
> **Codigo frontend (15s):** Mostrar estructura features/. Mostrar useProductos.ts con useQuery. Mostrar queryKeys.ts.
>
> **Demo (10s):** Navegar entre features, mostrar responsive mobile, badge WS.

---

## Bloque 7 — Cierre (1:00)

### Slide 13 | Resumen Final (1:00)

> **En pantalla:** Diagrama final + stack:
> ```
> [PostgreSQL] ← [SQLModel] ← [Service Layer] ← [REST API] ← [React/Postman]
> 
> Stack: FastAPI + SQLModel + PostgreSQL | JWT + bcrypt + RBAC
> ORM: constraints + soft delete + snapshots | Repository + UoW
> WebSockets con rooms | MercadoPago (SDK + webhook)
> Cloudinary (upload + transforms) | 155 tests | 69% coverage
> React 19 + TypeScript + Zustand + TanStack Query + Tailwind
> Feature-sliced + mobile-first + Docker
> ```
>
> **Narracion:** "Todo arranca en la base de datos y sube hasta el cliente. La API REST es el contrato unico. El backend concentra reglas de negocio y seguridad. El frontend es una de las caras de la API. Eso es lo que construimos: un sistema donde el backend es la fuente de verdad, con arquitectura limpia, testeado, y listo para produccion."

---

## Notas para el presentador

- **Ritmo:** ~65s por slide. Slides densos (2, 7, 8) ~1:15-1:45, ligeros (1, 5, 10) ~0:45.
- **Codigo:** NO leas linea por linea. Senala estructura y explica proposito.
- **Demo frontend:** Mostralo para ver como se consume la API, no para explicar React.
- **Swagger backup:** Si el frontend falla, abri `/docs` y mostra los endpoints.
- **Preparacion:**
  - ADMIN logueado en frontend y Swagger.
  - Backend corriendo, BD con seed.
  - Docker opcional: `docker-compose up`.
- **MercadoPago:** Se honesto — explica la arquitectura, mostra el codigo, conta que paso.
- **Tiempo:** 13 slides × ~65s = ~14 minutos. Practica la narracion en voz alta.
