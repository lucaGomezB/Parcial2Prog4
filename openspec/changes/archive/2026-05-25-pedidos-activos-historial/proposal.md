## Why

Actualmente el panel de pedidos solo muestra pedidos activos (no terminales). El usuario no puede consultar el historial de pedidos entregados o cancelados. Se necesita separar la vista en dos modos para dar visibilidad completa del ciclo de vida de los pedidos.

## What Changes

- Agregar un endpoint `GET /pedidos/historial` que retorne pedidos en estado terminal (ENTREGADO, CANCELADO)
- Para ADMIN/PEDIDOS: retorna todos los pedidos terminales
- Para CLIENT: retorna solo sus pedidos terminales
- Modificar `PedidosPage` del frontend para mostrar dos pestañas/tabs: "Activos" y "Historial"
- La pestaña "Activos" mantiene el comportamiento actual (pedidos no terminales)
- La pestaña "Historial" muestra los pedidos terminales, llamando al nuevo endpoint

## Capabilities

### New Capabilities
- `order-history`: Consulta de historial de pedidos con filtro por estados terminales, con permisos diferenciados por rol

### Modified Capabilities
- Ninguna. No cambian requisitos existentes, solo se agrega nueva funcionalidad.

## Impact

- **Backend**: Nuevo endpoint `GET /pedidos/historial` + métodos `get_historial()` y `get_historial_by_usuario()` en `PedidoService`
- **Frontend**: `PedidosPage.tsx` se modifica para incluir tabs y llamar al nuevo endpoint
- **API**: Extensión de la API de pedidos, sin cambios breaking
