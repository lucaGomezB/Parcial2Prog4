## 1. Backend — FSM en service

- [x] 1.1 Agregar `TRANSICIONES_VALIDAS` dict en PedidoService con las transiciones permitidas del FSM
- [x] 1.2 Implementar `avanzar_estado(session, pedido_id, usuario)` que valide la transición, actualice `estado_codigo` en Pedido, y cree un registro en HistorialEstadoPedido (INSERT-only)
- [x] 1.3 Implementar `cancelar_pedido(session, pedido_id, usuario)` que valide permisos (ADMIN/PEDIDOS siempre, usuario común solo antes de EN_CAMINO) y ejecute la cancelación

## 2. Backend — Endpoints

- [x] 2.1 Agregar `GET /pedidos/activos` que retorne pedidos con estado no terminal, ordenados por created_at DESC
- [x] 2.2 Agregar `POST /pedidos/{id}/avanzar` que llame a `avanzar_estado()` en service
- [x] 2.3 Agregar `POST /pedidos/{id}/cancelar` que llame a `cancelar_pedido()` en service
- [x] 2.4 Agregar schemas `PedidoAvanzarResponse` y `PedidoCancelarResponse`

## 3. Frontend — Página de Gestión de Pedidos

- [x] 3.1 Crear `src/pages/PedidosPage.tsx` con tabla de pedidos activos
- [x] 3.2 Llamada a GET /pedidos/activos (gestores) o /mis-pedidos (clientes)
- [x] 3.3 Botón Avanzar con texto dinámico (Confirmar → Preparar → Enviar → Entregar)
- [x] 3.4 Botón Cancelar para gestores y usuarios comunes (antes de EN_CAMINO)
- [x] 3.5 Popup de Detalles con DetallePedido (producto, cantidad, precio, subtotal)
- [x] 3.6 Formateo de fechas, colores por estado, montos con $

## 4. Frontend — Conectar "Realizar Pedido"

- [x] 4.1 Carrito crea pedido via POST /pedidos/ + POST /pedidos/{id}/avanzar
- [x] 4.2 Clear carrito + redirección a /pedidos después de crear
- [x] 4.3 Manejo de errores con mensaje visible

## 5. Frontend — Navegación

- [x] 5.1 Ruta /pedidos → <PedidosPage /> en App.tsx (todos los roles)
- [x] 5.2 Link "Pedidos" en nav para ADMIN y PEDIDOS
- [x] 5.3 CLIENT puede acceder a /pedidos (ve solo sus pedidos via /mis-pedidos)
