## Context

El backend de Food Store actualmente tiene dos bounded contexts implementados: `CatalogoDeProductos` (Categorías, Productos, Ingredientes) e `IdentidadYAcceso` (Usuarios, Roles, Auth, Direcciones, RefreshTokens). El tercer contexto `VentasPagosTrazabilidad` existe solo como directorios vacíos — no tiene models, repos, services, schemas ni routers.

El flujo de imports es estrictamente `Router → Service → UoW → Repository → Model`. Cada bounded context tiene su propio `UnitOfWork`. Los catálogos (Rol, EstadoPedido, FormaPago) usan PK semántica (VARCHAR) para legibilidad en JWTs y queries.

```
Router → Service → UoW → Repository → Model
```

## Goals / Non-Goals

**Goals:**
- Crear el módulo `VentasPagosTrazabilidad` completo con 6 entidades (Pedido, DetallePedido, EstadoPedido, FormaPago, HistorialEstadoPedido, Pago)
- Implementar FSM de 6 estados para Pedido con validación de transiciones
- Snapshot de precios en Pedido y DetallePedido (inmutables al crear)
- HistorialEstadoPedido append-only (solo INSERT, ni UPDATE ni DELETE)
- Agregar relación Usuario → Pedido (1:N)
- Refinar UsuarioRol con PK compuesta `(usuario_id, rol_codigo)` + campos extendidos
- Seed completo que incluya EstadoPedido y FormaPago
- Seguir exactamente el patrón existente (models → repository → service → schemas → router + UoW)

**Non-Goals:**
- NO se implementan endpoints de pago con MercadoPago (solo el modelo Pago)
- NO se implementa lógica de webhooks IPN
- NO se implementa la lógica de negocio de la FSM (solo el modelo y seed)
- NO se implementa el módulo Cocina (pantalla de cocina)
- NO se implementan tests en esta etapa

## Decisions

### 1. PK semántica (VARCHAR) para catálogos
**Decisión**: EstadoPedido y FormaPago usan PK semántica (`codigo: str` con `primary_key=True`) como Rol.
**Rationale**: Consistencia con el patrón existente de Rol. Permite FK legibles en los datos y en payloads JWT. Evita joins innecesarios para mostrar el estado actual.
**Alternativa**: PK autoincremental INT — rechazada porque perderíamos legibilidad en las tablas y tendríamos que hacer joins constantes.

### 2. SQLModel con `table=True` directamente
**Decisión**: Usar SQLModel igual que el resto del proyecto (no SQLAlchemy raw).
**Rationale**: Consistencia total con el código existente. El mixin `TimestampModel` y `SoftDeleteModel` ya están definidos en `models/base.py`.

### 3. Snapshot en DetallePedido y Pedido
**Decisión**: DetallePedido captura `nombre_snapshot`, `precio_snapshot`, `subtotal_snap` al crearse. Pedido almacena `subtotal`, `descuento`, `costo_envio`, `total` como snaps.
**Rationale**: Regla de negocio RN-04 del ERD v5. Los precios de productos pueden cambiar, pero el pedido debe reflejar el precio al momento de la compra.

### 4. DetallePedido sin updated_at
**Decisión**: DetallePedido NO hereda de TimestampModel, solo tiene `created_at`.
**Rationale**: Es una fila inmutable por diseño (RN-04). Si se necesita corregir, se cancela el pedido y se crea uno nuevo. Consistente con HistorialEstadoPedido que también es append-only.

### 5. Personalización con INTEGER[] (array PostgreSQL)
**Decisión**: `personalizacion` es `Optional[List[int]]` mapeado a INTEGER[] de PostgreSQL, que contiene IDs de ingredientes removidos.
**Rationale**: ERD v5 reemplaza el JSONB v3 por array nativo PostgreSQL. Más eficiente y tipado.

### 6. UoW separado para VentasPagosTrazabilidad
**Decisión**: Nuevo `VentasPagosTrazabilidadUnitOfWork` en `modules/VentasPagosTrazabilidad/uow.py`.
**Rationale**: Sigue el patrón exacto de `CatalogoDeProductosUnitOfWork` e `IdentidadYAccesoUnitOfWork`. Cada bounded context tiene su propio UoW.

### 7. UsuarioRol con PK compuesta
**Decisión**: Migrar de `id` surrogate a PK compuesta `(usuario_id, rol_codigo)`.
**Rationale**: El ERD v5 define PK compuesta. Evita duplicados a nivel BD sin necesidad de unique constraints adicionales. Agrega campos `asignado_por_id` (FK a Usuario) y `expires_at`.

### 8. Seed unificado en `scripts/sprint_seed.py`
**Decisión**: Agregar seed de EstadoPedido y FormaPago al script existente `sprint_seed.py`.
**Rationale**: Un solo script para todo el seed. Se ejecuta con `python scripts/sprint_seed.py`. Ya maneja roles, usuarios, categorías, ingredientes, productos.

## Risks / Trade-offs

- **Riesgo: ON DELETE RESTRICT en DetallePedido.producto_id** → Si un producto tiene pedidos asociados, no se podrá eliminar. Mitigación: usar soft-delete en Producto (ya implementado).
- **Riesgo: Personalización con INTEGER[]** → Si se elimina un ingrediente referenciado en un array existente, el array queda con IDs huérfanos. Mitigación: los ingredientes usan soft-delete, y la personalización es un snapshot.
- **Trade-off: Sin updated_at en DetallePedido e HistorialEstadoPedido** → No se puede saber cuándo se modificó, pero es intencional (inmutabilidad).
- **Riesgo: PK compuesta en UsuarioRol** → Si un usuario necesita el mismo rol dos veces (no debería), la PK lo impide. Esto es correcto.
