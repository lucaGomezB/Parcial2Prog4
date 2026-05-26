## Why

El sistema tiene toda la infraestructura de pedidos (Pedido, DetallePedido, HistorialEstadoPedido, EstadoPedido) pero no hay una interfaz para gestionarlos. Los usuarios no pueden ver sus pedidos, ni los administradores/gestionadores pueden avanzar el estado de los mismos.

## What Changes

1. **Backend — FSM en service**: Agregar método `avanzar_estado()` en PedidoService con validación de máquina de estados (CONFIRMADO → EN_PREP → EN_CAMINO → ENTREGADO/CANCELADO). Las transiciones se validan en service, NUNCA en router.
2. **Backend — Cancelar**: Método `cancelar_pedido()` que transiciona a CANCELADO y registra en HistorialEstadoPedido.
3. **Backend — Endpoints**: `POST /pedidos/{id}/avanzar` y `POST /pedidos/{id}/cancelar`.
4. **Backend — Filtro activos**: Endpoint `GET /pedidos/activos` que excluye estados terminales (ENTREGADO, CANCELADO).
5. **Frontend — Página Gestión de Pedidos**: Nueva página `PedidosPage.tsx` con tabla de pedidos activos ordenados por fecha descendente.
6. **Frontend — Popup de detalles**: Modal con DetallePedido (producto, cantidad, precio snapshot, subtotal).
7. **Frontend — Botones de acción**: Avanzar estado (FSM) y Cancelar pedido, visibles según rol.
8. **Frontend — "Realizar Pedido" funcional**: El botón en Carrito crea el pedido y lo avanza a CONFIRMADO.
9. **Frontend — Navegación**: Link "Pedidos" visible para ADMIN y PEDIDOS.

## Capabilities

### New Capabilities
- `order-management`: Gestión de pedidos con FSM, avance de estado, cancelación, visualización de detalles y filtro de pedidos activos.

### Modified Capabilities
<!-- Sin cambios en specs existentes -->

## Impact

- **Backend**: `modules/VentasPagosTrazabilidad/Pedido/service.py` — nuevos métodos `avanzar_estado()`, `cancelar_pedido()`, `get_activos()`.
- **Backend**: `modules/VentasPagosTrazabilidad/Pedido/router.py` — nuevos endpoints `/avanzar`, `/cancelar`, `/activos`.
- **Frontend**: Nueva `src/pages/PedidosPage.tsx`.
- **Frontend**: `src/pages/Carrito.tsx` — botón "Realizar Pedido" funcional.
- **Frontend**: `src/App.tsx` — ruta `/pedidos`, nav link.
- **Backend**: `HistorialEstadoPedido` se usa como append-only (INSERTs only).
