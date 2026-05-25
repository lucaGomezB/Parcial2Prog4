## ADDED Requirements

### Requirement: Sistema crea pedidos con datos snapshot

El sistema SHALL crear pedidos con `usuario_id` (obligatorio), `direccion_id` (opcional, NULL = retiro en local), `estado_codigo` (default PENDIENTE), `forma_pago_codigo` (obligatorio), y snaps monetarios (`subtotal`, `descuento` default 0.00, `costo_envio` default 50.00, `total` = subtotal - descuento + costo_envio).

#### Scenario: Creación de pedido básico
- **WHEN** se crea un pedido con subtotal = 100.00, descuento = 0.00, costo_envio = 50.00
- **THEN** el total se calcula como 150.00
- **THEN** el estado inicial es PENDIENTE

#### Scenario: Pedido con retiro en local
- **WHEN** se crea un pedido sin direccion_id
- **THEN** direccion_id es NULL
- **THEN** costo_envio es 0.00

### Requirement: Pedido usa FSM de 6 estados con validación de transiciones

El sistema SHALL validar las transiciones de estado del pedido según la FSM. Transiciones permitidas: PENDIENTE→CONFIRMADO, PENDIENTE→CANCELADO, CONFIRMADO→EN_PREP, CONFIRMADO→CANCELADO, EN_PREP→EN_CAMINO, EN_PREP→CANCELADO, EN_CAMINO→ENTREGADO. Estados terminales (ENTREGADO, CANCELADO) no admiten transiciones salientes.

#### Scenario: Transición válida PENDIENTE→CONFIRMADO
- **WHEN** se cambia estado de PENDIENTE a CONFIRMADO
- **THEN** la transición es aceptada
- **THEN** se registra en HistorialEstadoPedido

#### Scenario: Transición inválida PENDIENTE→EN_CAMINO
- **WHEN** se intenta cambiar de PENDIENTE a EN_CAMINO
- **THEN** el sistema rechaza la transición con error 400

#### Scenario: Estado terminal no acepta transiciones
- **WHEN** se intenta cambiar de ENTREGADO a cualquier estado
- **THEN** el sistema rechaza la transición con error 400

### Requirement: DetallePedido captura snapshot de producto

Cada DetallePedido SHALL tener PK compuesta `(pedido_id, producto_id)` y capturar `nombre_snapshot`, `precio_snapshot` y `subtotal_snap` al momento de creación. `cantidad` >= 1, `personalizacion` es INTEGER[] con IDs de ingredientes removidos. NO tiene `updated_at` (fila inmutable).

#### Scenario: Creación de detalle con snapshot
- **WHEN** se agrega un detalle con producto X (precio 100.00, nombre "Coca Cola"), cantidad 2
- **THEN** `nombre_snapshot` = "Coca Cola"
- **THEN** `precio_snapshot` = 100.00
- **THEN** `subtotal_snap` = 200.00
- **THEN** el total del pedido se actualiza

#### Scenario: Personalización con ingredientes removidos
- **WHEN** se crea detalle con personalizacion = [3, 7]
- **THEN** el array INTEGER[] se guarda correctamente
- **THEN** los IDs 3 y 7 corresponden a ingredientes removidos

### Requirement: HistorialEstadoPedido es append-only

Cada cambio de estado SHALL registrar una entrada en HistorialEstadoPedido con `pedido_id`, `estado_desde` (NULL en transición inicial), `estado_hacia`, `usuario_id` (NULL = sistema), `motivo` (obligatorio si estado_hacia = CANCELADO). Solo soporta INSERT — ni UPDATE ni DELETE.

#### Scenario: Registro de transición inicial
- **WHEN** se crea un pedido nuevo
- **THEN** se registra historial con estado_desde = NULL, estado_hacia = PENDIENTE, usuario_id = NULL

#### Scenario: Cancelación requiere motivo
- **WHEN** se cancela un pedido
- **THEN** el campo motivo NO puede ser NULL
- **THEN** el historial registra estado_hacia = CANCELADO

#### Scenario: Append-only enforcement
- **WHEN** se intenta UPDATE o DELETE en HistorialEstadoPedido
- **THEN** el sistema rechaza la operación
