## Context

El panel de pedidos actualmente carga `GET /pedidos/activos` que retorna solo pedidos en estados no terminales. No existe forma de ver pedidos entregados o cancelados. La página `PedidosPage.tsx` ya maneja correctamente roles (CLIENT vs ADMIN/PEDIDOS) usando `esGestor`.

## Goals / Non-Goals

**Goals:**
- Proveer un endpoint `GET /pedidos/historial` que retorne pedidos en estados terminales (ENTREGADO, CANCELADO)
- Soporte para ambos modos de acceso: ADMIN/PEDIDOS ven todos, CLIENT ve solo los suyos
- Agregar tabs "Activos" | "Historial" en el frontend sin perder funcionalidad existente

**Non-Goals:**
- No cambiar el endpoint `GET /pedidos/activos` existente
- No modificar el modelo de datos ni la FSM de estados
- No agregar paginación avanzada ni filtros adicionales

## Decisions

1. **Nuevo endpoint vs query param**: Se opta por un nuevo endpoint `GET /pedidos/historial` en lugar de agregar un query param a `GET /pedidos/activos`. Esto mantiene la API REST limpia (cada recurso tiene su URL) y evita romper el comportamiento actual.

2. **Métodos de service**: Se crean `get_historial()` y `get_historial_by_usuario()` siguiendo el mismo patrón que `get_activos()` y el filtro inline en `read_activos()`. No se reutilizan los mismos métodos porque la lógica de filtrado es diferente (terminal vs no terminal).

3. **Frontend con tabs simples**: Se usa estado local `modo: 'activos' | 'historial'` con dos botones/tabs. No se introduce router state ni URL params para mantenerlo simple. La recarga de datos ocurre al cambiar de tab.

4. **Mismo componente, no ruta separada**: Se mantiene todo en `PedidosPage.tsx` con un condicional de modo, en lugar de crear una ruta separada `/pedidos/historial`. Menos cambios en el router y mejor UX.

## Risks / Trade-offs

- [Carga duplicada] Si el usuario alterna tabs frecuentemente, se hacen llamadas API repetidas. → Mitigación: caché simple con useState, solo recarga si cambia el tab.
- [Consistencia] Si un pedido cambia de estado mientras se ve el historial, podría aparecer en ambos tabs. → Mitigación: es comportamiento esperado, los endpoints son point-in-time.
