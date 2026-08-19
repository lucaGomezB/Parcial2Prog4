# AGENTS.md — Convenciones del Proyecto

Reglas de arquitectura y convenciones que TODO agente de IA DEBE seguir al generar o modificar
codigo en este proyecto. Este es el contrato unico de arquitectura para frontend y backend.

---

## Stack Tecnologico

| Capa | Tecnologia |
|------|-----------|
| Frontend | React 19, TypeScript 6, Vite 8, Tailwind 4, React Router 7, Zustand 5, TanStack Query/Form, Recharts 3 |
| Backend | Python 3.12, FastAPI, SQLModel, PostgreSQL 16, Alembic, pytest |
| Infra | Docker Compose, Nginx |

---

## Frontend

### Arquitectura: Feature-Sliced Design (OBLIGATORIO)

Toda feature de negocio reside en `App/Frontend/src/features/<nombre>/` con esta estructura
interna (solo los subdirectorios necesarios, no todos):

```
features/<feature>/
├── api/          # Cliente HTTP para endpoints de esta feature
├── components/   # Componentes visuales de esta feature
├── hooks/        # Custom hooks de esta feature
├── pages/        # Paginas/rutas de esta feature
├── store/        # Estado global de esta feature (Zustand)
└── types/        # Tipos TypeScript de esta feature
```

### Shared layer (`src/shared/`)

SOLO codigo usado por 2+ features. Si una sola feature lo usa, DEBE estar dentro
de esa feature. Contiene:

- `shared/api/` — cliente HTTP (Axios), uploads (Cloudinary), y query keys (TanStack Query)
- `shared/components/` — componentes reusables (DataTable, ImageCarousel, Modal, Skeleton, Toast)
- `shared/hooks/` — hook de formulario base (useAppForm)
- `shared/store/` — stores globales (authStore, cartStore, filtrosStore, uiStore)
- `shared/utils/` — utilidades (exportExcel)

### Flujo de imports (DE ARRIBA HACIA ABAJO)

```
Pages → Hooks → API → Types
```

- Pages PUEDEN importar hooks, API, y tipos
- Hooks PUEDEN importar API, stores, y tipos
- API SOLO PUEDE importar `shared/api/client` y tipos locales
- Tipos NO PUEDEN importar nada (son hojas del arbol de dependencias)

### Alias `@/` (OBLIGATORIO)

Todos los imports DEBEN usar el alias `@/` que resuelve a `src/`. Prohibidos los
imports relativos con `../`.

```ts
// CORRECTO
import { useAuthStore } from '@/shared/store/authStore'
import { productosApi } from '@/features/productos/api/productos'

// INCORRECTO
import { useAuthStore } from '../../shared/store/authStore'
```

### Cross-feature imports (SOLO API)

Cuando una feature necesita datos de otra, SOLO puede importar su modulo de API.
NUNCA componentes, hooks, paginas, o stores de otra feature.

```ts
// VALIDO: Carrito (pedidos) importa API de productos
import { productosApi } from '@/features/productos/api/productos'

// INVALIDO: importar componente de otra feature
import ProductCard from '@/features/productos/components/ProductCard'
```

### App shell (`src/app/`)

Contiene EXCLUSIVAMENTE el cascaron de la aplicacion:

- `App.tsx` — bootstrap de sesion, barra de navegacion, renderizado de rutas
- `router.tsx` — componente puro que recibe flags de rol y retorna `<Routes>`
- `main.tsx` — punto de entrada, monta React con BrowserRouter
- `queryClient.ts` — configuracion de TanStack Query (stale time, retries)
- `App.css`, `index.css` — estilos globales

NO contiene logica de negocio ni estado de features.

### Excepcion documentada

`shared/api/client.ts` importa `shared/store/authStore` para obtener el token JWT.
Esto es aceptable porque authStore es infraestructura compartida, no logica de una
feature individual.

### Prohibiciones

- NO imports circulares
- NO imports relativos (`../`)
- NO cross-feature imports de componentes, paginas, stores, o hooks
- NO logica de features en `shared/` (YAGNI: no compartir prematuramente)

### Features del proyecto

| Feature (frontend) | Modulo backend asociado | Responsabilidad |
|---|---|---|
| `auth/` | IdentidadYAcceso | Login, registro, admin de usuarios |
| `categorias/` | CatalogoDeProductos/Categoria | CRUD de categorias |
| `productos/` | CatalogoDeProductos/Producto | CRUD de productos, detalle publico |
| `unidades-medida/` | CatalogoDeProductos/UnidadMedida | CRUD de unidades de medida |
| `pedidos/` | VentasPagosTrazabilidad | Carrito, checkout, seguimiento, pagos |
| `estadisticas/` | Estadisticas | Dashboard KPIs y graficos |

---

## Backend

### Arquitectura modular

Proyecto FastAPI organizado en modulos de dominio en `modules/` con bounded contexts:

| Modulo | Responsabilidad |
|--------|----------------|
| IdentidadYAcceso | Autenticacion JWT, refresh tokens, usuarios, roles |
| CatalogoDeProductos | Productos, categorias, ingredientes, unidades de medida |
| VentasPagosTrazabilidad | Pedidos, pagos (MercadoPago), carrito snapshots, direcciones |
| Estadisticas | Dashboard KPIs, graficos |
| Uploads | Imagenes via Cloudinary |

### Estructura de sub-modulos

Cada modulo de dominio contiene sub-modulos que encapsulan una entidad o
conjunto de entidades relacionadas. Ejemplo de `VentasPagosTrazabilidad`:

```
VentasPagosTrazabilidad/
├── uow.py                    # Unit of Work del modulo (inyecta repositorios)
├── Pedido/                   # Sub-modulo: pedidos
│   ├── models.py
│   ├── schemas.py
│   ├── repository.py
│   ├── service.py
│   └── router.py
├── DetallePedido/            # Sub-modulo: lineas del pedido
├── Pago/                     # Sub-modulo: pagos y webhook MercadoPago
├── CarritoSnapshot/           # Sub-modulo: snapshots del carrito pre-pago
├── EstadoPedido/             # Sub-modulo: catalogo de estados
├── HistorialEstadoPedido/    # Sub-modulo: bitacora de cambios de estado
└── FormaPago/                # Sub-modulo: catalogo de formas de pago
```

### Patron de capas (ESTRICTO)

```
Router → Service → Unit of Work → Repository → SQLModel
```

- Routers: solo reciben requests, validan, delegan al servicio
- Services: logica de negocio, transacciones, llamadas a UoW
- Unit of Work: coordina transacciones, inyecta repositorios
- Repositories: queries SQLModel, operaciones CRUD
- NO logica de negocio en routers
- NO queries raw fuera de repositorios

### Convenciones de datos

- **Dinero**: SIEMPRE `Decimal` (nunca `float`)
- **Soft delete**: campo `activo` (boolean, default `True`); filtrado automatico
- **Timestamps**: `created_at`, `updated_at` en UTC; `deleted_at` para soft delete
- **API**: prefijo `/api/v1/`, respuestas paginadas `{ items, total, skip, limit }`
- **Errores**: RFC 7807 Problem Details (`type`, `title`, `status`, `detail`)

### Autenticacion y autorizacion

- JWT access token (corto, en memoria/sessionStorage)
- Refresh token en httpOnly cookie (inaccesible desde JavaScript)
- RBAC con roles: ADMIN, CLIENT, STOCK, PEDIDOS
- Roles planos: cada endpoint lista explicitamente los roles permitidos via require_roles(). No existe jerarquia de herencia entre roles. El seeder asigna un rol por usuario. Cada endpoint declara que roles pueden acceder.

### WebSocket

- Autenticacion JWT en handshake (?token=...)
- Broadcast post-commit (eventos se emiten despues del commit exitoso)
- Canales: `/api/v1/pedidos/ws/pedidos/{id}` (cliente), `/api/v1/pedidos/ws/admin/pedidos` (staff)
- Eventos: `estado_cambiado`, `pedido_cancelado`, `pago_confirmado`

### Seeders

- Idempotentes: verifican existencia antes de insertar
- Crean roles, usuarios de prueba, y datos de ejemplo
- Se ejecutan automaticamente en `docker-compose up`

### Prohibiciones

- NO logica de negocio en routers
- NO queries SQL raw fuera de repositorios
- NO `float` para dinero (usar `Decimal`)
- NO eliminar dependencias del Unit of Work (los servicios dependen de UoW, no de repositorios directamente)

---

## Testing

### Backend

- **Runner**: `pytest App/Backend/tests/` (con `pytest-cov` para cobertura)
- **Base de datos**: SQLite en memoria (`:memory:`) con `StaticPool`. Cada test corre
  dentro de una transaccion que se revierte al finalizar -- tests 100% aislados.
- **Fixtures compartidos**: `conftest.py` (467 lineas) provee:
  - `engine` (session-scoped): engine SQLite en memoria
  - `db_session` (function-scoped): sesion transaccional con rollback automatico
  - `client` (function-scoped): TestClient de FastAPI con override de sesion
  - Headers de auth por rol: `admin_headers`, `client_headers`, `pedidos_headers`
  - Seeders: `_seed_roles`, `_seed_estados_pedido`, `_seed_formas_pago`
  - Factories: `producto_factory`, `categoria_factory`, `ingrediente_factory`,
    `pedido_factory`, `direccion_factory`
- **Convencion de nombres**: `test_<modulo>.py`, clases `Test<Comportamiento>`,
  metodos `test_<accion_esperada>`
- **Estrategia de capas**: servicios y repositorios se testean via TestClient
  (integracion). No se mockea la base de datos.
- **WebSocket**: `test_websocket.py` prueba los endpoints reales con TestClient

Archivos de test existentes (12):

| Archivo | Modulo testeado |
|---|---|
| `test_identidad_acceso.py` | Auth, usuarios, roles |
| `test_catalogo_productos.py` | Productos, categorias |
| `test_unidad_medida.py` | Unidades de medida |
| `test_pedidos.py` | Pedidos |
| `test_catalogos_pedido.py` | Estados, formas de pago |
| `test_pedido_post_pago.py` | Flujo post-pago MercadoPago |
| `test_pago_service.py` | Servicio de pagos |
| `test_historial_estado_pedido_service.py` | Historial de estados |
| `test_estadisticas.py` | Dashboard KPIs |
| `test_websocket.py` | WebSocket pedidos/admin |
| `test_cloudinary_uploads.py` | Uploads a Cloudinary |

### Frontend

- **No hay tests** de frontend (`vitest`, `jest`, o `testing-library` no estan
  instalados en `package.json`). Esto es deuda tecnica conocida.

---

## Reglas generales

- AGENTS.md es la UNICA fuente de verdad de arquitectura para agentes
- Mantener AGENTS.md actualizado con cada cambio de arquitectura
- Idioma: documentacion en espanol, codigo en ingles
- Las reglas en AGENTS.md son MANDATORIAS, no sugerencias
