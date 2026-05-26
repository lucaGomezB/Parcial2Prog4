## 1. Backend — Service

- [x] 1.1 Agregar método `get_historial()` en `PedidoService` que retorne pedidos con estado ENTREGADO o CANCELADO
- [x] 1.2 Agregar método `get_historial_by_usuario()` en `PedidoService` que retorne solo los terminales de un usuario

## 2. Backend — Router

- [x] 2.1 Agregar endpoint `GET /pedidos/historial` con lógica de roles: ADMIN/PEDIDOS ven todos, CLIENT ve solo los suyos

## 3. Frontend — PedidosPage

- [x] 3.1 Agregar tabs "Activos" | "Historial" con estado local `modo`
- [x] 3.2 Conectar tab "Activos" a `GET /pedidos/activos` y tab "Historial" a `GET /pedidos/historial`
- [x] 3.3 Ocultar botones "Avanzar" y "Cancelar" en modo historial

## 4. Frontend — API client

- [x] 4.1 Agregar método `getHistorial()` al `pedidosApi`
