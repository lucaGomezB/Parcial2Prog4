## Context

Actualmente `PedidoService.cancelar_pedido` permite cancelación a usuarios con rol ADMIN o PEDIDOS desde cualquier estado no terminal, y a usuarios comunes (CLIENTE) desde cualquier estado anterior a EN_CAMINO (PENDIENTE, CONFIRMADO, EN_PREP). La regla de negocio requiere que EN_PREP quede restringido solo a ADMIN/PEDIDOS.

El cambio es puramente de lógica de autorización — no afecta modelo de datos, esquemas, ni frontend.

## Goals / Non-Goals

**Goals:**
- Usuarios CLIENTE solo pueden cancelar pedidos en estado PENDIENTE o CONFIRMADO
- ADMIN y PEDIDOS pueden cancelar desde cualquier estado no terminal (sin cambios)

**Non-Goals:**
- No se cambia la FSM ni los estados del pedido
- No se agregan ni modifican endpoints
- No se toca el frontend

## Decisions

| Decisión | Alternativa | Razón |
|----------|-------------|-------|
| Cambiar umbral de `>= 4` a `>= 3` en service.py | Agregar una lista explícita de estados permitidos | El cambio mínimo es más seguro y la lógica existente ya usa el ordenamiento numérico. Sin embargo, una lista explícita es más mantenible. Se opta por **lista explícita** para claridad: `estados_permitidos_cliente = {"PENDIENTE", "CONFIRMADO"}` |

## Risks / Trade-offs

- **[Bajo]** Un cliente podría tener el botón de cancelar visible en EN_PREP y recibir un 403 del backend → mitigar actualizando el frontend para ocultar el botón en EN_PREP para roles CLIENTE.
- **[Bajo]** Si en el futuro se agregan nuevos estados, la lista explícita requerirá actualización manual → se considera aceptable.
