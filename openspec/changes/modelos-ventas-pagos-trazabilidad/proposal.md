## Why

El módulo `VentasPagosTrazabilidad` existe como directorio vacío — no tiene models, repository, service, schemas ni router. Sin estas entidades no es posible gestionar pedidos, pagos ni la trazabilidad de cambios de estado, que son el core del negocio. Además, el modelo `Usuario` actual no tiene relación con `Pedido`, y el seed carece de datos para los nuevos catálogos (estados de pedido, formas de pago).

## What Changes

- **Creación completa del módulo `VentasPagosTrazabilidad`** con 6 entidades:
  - `EstadoPedido` (catálogo semilla — 6 estados FSM)
  - `FormaPago` (catálogo semilla — 3 formas de pago)
  - `Pedido` (entidad principal con FSM, snaps monetarios, FK a EstadoPedido, FormaPago, Usuario, DireccionEntrega)
  - `DetallePedido` (PK compuesta, snaps de producto, personalización con INTEGER[])
  - `HistorialEstadoPedido` (append-only, trazabilidad FSM)
  - `Pago` (integración con MercadoPago, triple unique)
- **Modificación de `Usuario`**: agregar relación 1:N con `Pedido`
- **Modificación de `UsuarioRol`**: migrar a PK compuesta `(usuario_id, rol_codigo)` + campos `asignado_por_id` y `expires_at`
- **UoW propio** para `VentasPagosTrazabilidad` siguiendo el patrón existente
- **Seed completo** que incluye: Roles, EstadosPedido, FormasPago, Usuarios y datos de catálogo existentes
- **Registro de modelos en `main.py`** para `SQLModel.metadata.create_all()` + inclusión de routers

## Capabilities

### New Capabilities
- `gestion-pedidos`: Creación y ciclo de vida de pedidos con FSM de 6 estados, detalles con snapshot de producto, historial append-only de cambios de estado
- `catalogos-pedido`: Catálogos semilla de EstadoPedido (6 estados FSM) y FormaPago (3 métodos), con PK semántica para legibilidad en JWT y datos
- `procesamiento-pagos`: Registro de pagos con integración MercadoPago (triple unique: mp_payment_id, external_reference, idempotency_key)

### Modified Capabilities
- `identidad-acceso`: Se modifica `Usuario` para agregar relación 1:N con `Pedido` y se refina `UsuarioRol` con PK compuesta y campos adicionales

## Impact

- **Backend**: Nuevo módulo `VentasPagosTrazabilidad/` con 6 sub-módulos (Pedido, DetallePedido, EstadoPedido, FormaPago, HistorialEstadoPedido, Pago) + UoW propio
- **Modelos existentes**: `Usuario` gana nueva relación; `UsuarioRol` migra a PK compuesta
- **Seed**: Se agregan datos para EstadoPedido y FormaPago; se unifica en `scripts/sprint_seed.py`
- **main.py**: Se agregan imports de nuevos modelos y routers
- **Dependencias**: Ninguna nueva — todo con SQLModel + FastAPI existentes
