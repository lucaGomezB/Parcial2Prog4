## MODIFIED Requirements

### Requirement: Actualizar detalle de pedido (refactor interno)
El sistema DEBE mantener el comportamiento actual del endpoint `PATCH /pedidos/{id}/detalles/{producto_id}` pero con la lógica implementada en el Service en vez del Router.

#### Scenario: Actualizar cantidad de detalle
- **WHEN** se envía `PATCH /pedidos/{id}/detalles/{producto_id}` con `cantidad > 0` en un pedido PENDIENTE
- **THEN** el detalle se actualiza con la nueva cantidad y subtotal, se recalcula el total del pedido, y se devuelve el pedido actualizado (comportamiento idéntico al actual)

#### Scenario: Eliminar detalle (cantidad = 0)
- **WHEN** se envía `PATCH /pedidos/{id}/detalles/{producto_id}` con `cantidad = 0`
- **THEN** el detalle se elimina, se recalcula el total, y se devuelve el pedido actualizado

#### Scenario: Error si pedido no está en PENDIENTE
- **WHEN** el pedido no está en estado PENDIENTE
- **THEN** responde con 400 "Solo se pueden modificar detalles en pedidos PENDIENTE"

### Requirement: Avanzar estado (refactor interno)
El sistema DEBE mantener el comportamiento actual del endpoint `POST /pedidos/{id}/avanzar` pero sin que el Router consulte directamente el historial.

#### Scenario: Avanzar devuelve estado anterior y actual
- **WHEN** se envía `POST /pedidos/{id}/avanzar`
- **THEN** la respuesta incluye `estado_anterior`, `estado_actual`, y `mensaje` (comportamiento idéntico al actual)
