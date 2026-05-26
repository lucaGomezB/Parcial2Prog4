## Context

El backend ya tiene toda la estructura: Pedido, DetallePedido (con snapshots inmutables), HistorialEstadoPedido (append-only), EstadoPedido (FSM con 6 estados). El service crea pedidos en PENDIENTE. No existe lógica de avance de estado ni endpoints para ello.

## Goals / Non-Goals

**Goals:**
- FSM con transiciones validadas en service: PENDIENTE → CONFIRMADO → EN_PREP → EN_CAMINO → ENTREGADO | CANCELADO
- Cancelación: ADMIN/PEDIDOS siempre pueden cancelar; usuarios comunes solo si estado está antes de EN_CAMINO
- HistorialEstadoPedido siempre INSERT, nunca UPDATE/DELETE
- Pedidos activos: excluir ENTREGADO y CANCELADO
- Popup de detalles con DetallePedido (producto, cantidad, precio, subtotal)
- "Realizar Pedido" desde carrito: crea order + avanza a CONFIRMADO
- Orden descendente por fecha de creación

**Non-Goals:**
- No pagos por ahora
- No actualización de contenidos del pedido (inmutable después de creado)
- No dirección de entrega en frontend (próximo change)

## Decisions

### 1. FSM validation in service
- `avanzar_estado()` recibe pedido_id + usuario que ejecuta
- El método valida la transición contra un dict de transiciones válidas
- Registra en HistorialEstadoPedido (INSERT) con estado_desde, estado_hacia, usuario_id
- Si la transición es inválida → HTTP 400

### 2. Cancelar vs Avanzar
- `cancelar_pedido()` es un método separado con su propia validación
- ADMIN/PEDIDOS: pueden cancelar cualquier pedido activo
- Usuario común: solo si estado está antes de EN_CAMINO

### 3. Creación de pedido desde carrito
- Frontend llama POST /pedidos/ con los items del carrito + forma de pago
- Backend crea el pedido en PENDIENTE con DetallePedido snapshots
- Frontend inmediatamente llama POST /pedidos/{id}/avanzar para pasar a CONFIRMADO

### 4. Pedidos activos
- Endpoint GET /pedidos/activos filtra WHERE estado_codigo NOT IN ('ENTREGADO', 'CANCELADO')
- ADMIN/PEDIDOS ven todos; usuarios ven solo los suyos (vía /mis-pedidos)
- Ordenado por created_at DESC

### 5. Frontend
- Tabla con columnas: ID, Usuario (solo ADMIN/PEDIDOS), Fecha, Estado, Total, Dirección (placeholder), Acciones
- Popup de detalles con DetallePedido al hacer clic en "Ver Detalles"

## Risks / Trade-offs

- **[Seguridad]**: El frontend llama a POST /pedidos/ + POST /pedidos/{id}/avanzar secuencialmente. Si el segundo falla, el pedido queda en PENDIENTE. El usuario puede reintentar.
- **[Concurrencia]**: Dos administradores avanzando el mismo pedido simultáneamente. El segundo recibirá error porque el estado ya no es el esperado. Se maneja con validación en service.
