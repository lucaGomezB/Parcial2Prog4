# Food Store — Sistema de Pedidos

## Integrantes

- **Luca Gomez**
- **Genaro Busto**

---

Enlace a la presentación: https://drive.google.com/file/d/1Yhj7-FECyTaSqpW8heZj5vt3VOEVM-6E/view?usp=sharing

Enlace a la carpeta de la presentación (incluye archivos de entorno): https://drive.google.com/drive/folders/1eL1ukyJYPUVEuQZbj4gkdoUGndr9u4U3?usp=sharing

---

## Descripcion

Food Store es un sistema e-commerce de gestion de pedidos de comida. Permite a los clientes registrarse, navegar un catalogo de productos con categorias e ingredientes, realizar pedidos con distintas formas de pago (incluyendo integracion con MercadoPago), y seguir el estado de sus pedidos en tiempo real mediante WebSockets. Incluye un modulo de estadisticas para administradores con KPIs de ventas, productos mas vendidos e ingresos, y un sistema de carga de imagenes via Cloudinary.

El backend esta construido con **Python FastAPI** siguiendo una arquitectura modular con separacion clara por modulos de dominio. El frontend esta construido con **React 19 + TypeScript + Vite + Tailwind CSS**.

---

## Stack Tecnologico

### Backend

| Tecnologia | Version | Proposito |
|------------|---------|-----------|
| Python | 3.12+ | Lenguaje principal |
| FastAPI | 0.115+ | Framework web asincronico |
| SQLModel | 0.0.38+ | ORM + validacion de datos |
| Pydantic | 2.13+ | Validacion y serializacion |
| PostgreSQL | 16 | Base de datos relacional |
| Alembic | latest | Migraciones de esquema |
| PyJWT + bcrypt | latest | Autenticacion JWT |
| SlowAPI | latest | Rate limiting |
| MercadoPago | 2.4.0 | Integracion de pagos |
| Cloudinary | 1.41+ | Almacenamiento de imagenes |

### Frontend

| Tecnologia | Version | Proposito |
|------------|---------|-----------|
| React | 19 | UI Library |
| TypeScript | 5.6+ | Tipado estatico |
| Vite | 6+ | Build tool y dev server |
| Tailwind CSS | 4 | Utilidades CSS |
| React Router | 7 | Ruteo declarativo |
| TanStack Query | latest | Fetching y cache de datos |
| Zustand | latest | Estado global |
| Recharts | latest | Graficos (dashboard) |

### Infraestructura

| Tecnologia | Proposito |
|------------|-----------|
| Docker + Docker Compose | Contenedores y orquestacion local |
| pytest + pytest-cov | Testing backend (155 tests) |
| SQLite (tests) | Base de datos en memoria para tests |

---

## Prerequisitos

### Con Docker (recomendado)

- [Docker](https://docs.docker.com/get-docker/) y [Docker Compose](https://docs.docker.com/compose/install/) instalados
- Git

### Sin Docker (setup manual)

- **Python 3.12+** con pip
- **Node.js 22+** con npm
- **PostgreSQL 16** corriendo localmente
- Git

---

## IMPORTANTE — Archivos .env

> **Los archivos `.env` con las credenciales reales NO estan en este repositorio.**
>
> Se encuentran en una carpeta compartida de Google Drive. Copia los siguientes archivos ANTES de ejecutar cualquier opcion de setup:
>
> - `App/Backend/.env` — credenciales de base de datos, MercadoPago, Cloudinary, JWT
> - `App/Frontend/.env` — URL del WebSocket
>
> **Link a Google Drive:** `[[Link a Google Drive — solicitar acceso]](https://drive.google.com/drive/folders/1um1ppNs72oW-bdTZ1v6Pb1Kv_U_dTru-?usp=sharing)`
>
> Sin estos archivos la aplicacion no funcionara. Las variables requeridas estan documentadas en `App/Backend/.env.example` y `App/Frontend/.env.example`.

---

## Opcion A: Setup con Docker (recomendado para el profesor)

Esta es la forma mas rapida de levantar todo el sistema. Docker Compose construye las imagenes, crea la base de datos, ejecuta las migraciones automaticamente al iniciar el backend, y levanta los tres servicios.

### Pasos

```bash
# 1. Clonar el repositorio
git clone [<url-del-repo>](https://github.com/lucaGomezB/Entrega_TPI_Prog4)
cd Entrega_TPI_Prog4

# 2. Copiar los archivos .env desde Google Drive a los roots de App\Backend y App\Frontend
#    (ver seccion IMPORTANTE arriba)

# 3. Levantar todos los servicios
docker-compose up --build
```

### URLs de acceso

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI JSON | http://localhost:8000/openapi.json |

---

## Opcion B: Setup Manual

### Backend (Python FastAPI)

```bash
# 1. Ubicarse en el directorio del backend
cd App/Backend

# 2. Crear y activar entorno virtual
python -m venv .venv

# En Windows:
.venv\Scripts\activate

# En Linux/Mac:
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Copiar el archivo .env desde Google Drive a App/Backend/.env
#    (ver seccion IMPORTANTE arriba)

# 5. Crear la base de datos PostgreSQL
#    El nombre de la BD debe coincidir con DATABASE_URL en tu .env
#    Ejemplo: psql -U postgres -c "CREATE DATABASE parcial_1_prog4_db;"

# 6. Ejecutar migraciones (el seed se ejecuta auto en el lifespan)
alembic upgrade head

# 7. Iniciar el servidor
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> **Nota sobre el seed de datos:** Al iniciar la aplicacion con `uvicorn main:app`, el hook `lifespan` de FastAPI ejecuta automaticamente `alembic upgrade head` y el seed de datos inicial (roles, productos, estados de pedido, etc.). Si necesitas ejecutar el seed manualmente sin levantar el servidor:
> ```bash
> python -m app.db.seed
> ```

### Frontend (React + Vite)

```bash
# 1. Ubicarse en el directorio del frontend
cd App/Frontend

# 2. Instalar dependencias
npm install

# 3. Copiar el archivo .env desde Google Drive a App/Frontend/.env
#    (ver seccion IMPORTANTE arriba)

# 4. Iniciar el servidor de desarrollo
npm run dev
```

El frontend estara disponible en **http://localhost:5173**.

---

## Testing

El backend cuenta con **155 tests** unitarios y de integracion que cubren todos los modulos del sistema. Se ejecutan con base de datos SQLite en memoria, sin necesidad de PostgreSQL.

```bash
# Ejecutar todos los tests
pytest App/Backend/tests/ -v

# Ejecutar tests con reporte de cobertura
pytest App/Backend/tests/ --cov=App/Backend -v
```

### Cobertura de tests por modulo

| Modulo | Tests | Archivo |
|--------|-------|---------|
| Auth (registro, login, logout, refresh, perfil) | 17 | `test_identidad_acceso.py` |
| Usuario (CRUD, RBAC, soft-delete) | 10 | `test_identidad_acceso.py` |
| Rol (listado, consulta) | 5 | `test_identidad_acceso.py` |
| Direccion de Entrega | 7 | `test_identidad_acceso.py` |
| Categoria (CRUD, arbol, jerarquia) | 7 | `test_catalogo_productos.py` |
| Producto (CRUD, soft-delete, categorias) | 7 | `test_catalogo_productos.py` |
| Ingrediente (CRUD, alergenos) | 7 | `test_catalogo_productos.py` |
| Pedido (listado, FSM avanzar/cancelar) | 18 | `test_pedidos.py` |
| Estado de Pedido (catalogos) | 5 | `test_catalogos_pedido.py` |
| Forma de Pago (catalogos) | 6 | `test_catalogos_pedido.py` |
| Estadisticas (KPIs, precision decimal) | 30 | `test_estadisticas.py` |
| Cloudinary (uploads, schemas, config) | 12 | `test_cloudinary_uploads.py` |
| Pago (MercadoPago init, webhook, consulta) | 10 | `test_pago_service.py` |
| Historial de Estado de Pedido | 5 | `test_historial_estado_pedido_service.py` |
| WebSocket (conexion, auth, canales) | 9 | `test_websocket.py` |

---

## Documentacion de la API

Una vez que el backend este corriendo, la documentacion interactiva de la API esta disponible en:

| Recurso | URL |
|----------|-----|
| **Swagger UI** | http://localhost:8000/docs |
| **ReDoc** | http://localhost:8000/redoc |
| **OpenAPI JSON** | http://localhost:8000/openapi.json |

Swagger UI permite probar los endpoints directamente desde el navegador usando el boton "Authorize" para autenticarse con JWT.

---

## Estructura del Proyecto

```
Entrega_TPI_Prog4/
├── docker-compose.yml
├── README.md
│
├── App/
│   ├── Backend/
│   │   ├── Dockerfile
│   │   ├── .dockerignore
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   ├── alembic.ini
│   │   ├── main.py                      # FastAPI app factory + lifespan
│   │   ├── app/core/                    # Infraestructura compartida
│   │   │   ├── database.py              # Engine SQLModel + get_session
│   │   │   ├── dependencies.py          # Dependencias FastAPI (roles, auth)
│   │   │   ├── security/                # JWT, hash passwords
│   │   │   ├── websocket_manager.py     # WebSocket para tracking de pedidos
│   │   │   ├── cloudinary_config.py     # Cliente Cloudinary
│   │   │   ├── problem_response.py      # RFC 7807 error responses
│   │   │   ├── paginated_response.py    # Paginacion estandar
│   │   │   └── rate_limit.py            # SlowAPI rate limiter
│   │   ├── modules/                     # Modulos de dominio (Clean Architecture)
│   │   │   ├── IdentidadYAcceso/        # Auth, Usuario, Rol, DireccionEntrega
│   │   │   ├── CatalogoDeProductos/     # Categoria, Producto, Ingrediente
│   │   │   ├── VentasPagosTrazabilidad/ # Pedido, EstadoPedido, FormaPago, Pago, Historial
│   │   │   ├── Estadisticas/            # Dashboard analytics
│   │   │   └── Uploads/                 # Cloudinary image management
│   │   ├── app/db/seed.py               # Seed de datos iniciales
│   │   ├── migrations/                  # Migraciones Alembic
│   │   └── tests/                       # Suite de tests (155 tests)
│   │
│   └── Frontend/
│       ├── Dockerfile
│       ├── .dockerignore
│       ├── .env.example
│       ├── package.json
│       ├── vite.config.ts
│       └── src/
│           ├── app/                     # App shell (App.tsx, router.tsx, main.tsx)
│           ├── assets/                  # Imagenes y recursos estaticos
│           ├── features/                # Feature-Sliced Design
│           │   ├── auth/                # Autenticacion y usuarios
│           │   ├── productos/           # Catalogo de productos e ingredientes
│           │   ├── pedidos/             # Pedidos, pagos y direcciones
│           │   ├── categorias/          # Categorias de productos
│           │   └── estadisticas/        # Dashboard KPIs y graficos
│           └── shared/                  # Codigo compartido entre features
│               ├── api/                 # Cliente HTTP (Axios) + query keys
│               ├── components/          # Componentes reusables (ImageCarousel)
│               ├── hooks/               # Hook de formulario base (useAppForm)
│               ├── store/               # Stores globales (authStore, cartStore)
│               └── utils/               # Utilidades (exportExcel)
│
└── openspec/                            # Especificaciones SDD (solo desarrollo)
```
