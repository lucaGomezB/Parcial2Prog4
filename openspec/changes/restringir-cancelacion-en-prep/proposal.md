## Why

Actualmente los usuarios comunes pueden cancelar pedidos hasta antes de EN_CAMINO, incluyendo el estado EN_PREP ("en preparación"). Esto permite que un cliente cancele un pedido que ya está siendo preparado activamente, causando pérdida de tiempo y recursos. Solo el personal con rol ADMIN o PEDIDOS debería poder cancelar pedidos que ya están en preparación.

## What Changes

- **Modificar lógica de cancelación** en `PedidoService.cancelar_pedido`: los usuarios comunes (CLIENTE) ya no podrán cancelar pedidos en estado `EN_PREP`. Solo podrán cancelar `PENDIENTE` y `CONFIRMADO`.
- ADMIN y PEDIDOS mantienen su capacidad de cancelar desde cualquier estado no terminal.
- **No requiere cambios de frontend** si el botón de cancelar ya se muestra condicionalmente según el backend (se recomienda validar igualmente).

## Capabilities

### New Capabilities

- (ninguna — es un cambio de regla de negocio, no una nueva capability)

### Modified Capabilities

- `gestion-pedidos`: Se modifica la regla de cancelación para el estado EN_PREP: solo ADMIN/PEDIDOS pueden cancelar en EN_PREP. Clientes solo pueden cancelar hasta CONFIRMADO.

## Impact

- **Backend**: `Backend/modules/VentasPagosTrazabilidad/Pedido/service.py` — cambiar el umbral de `>= 4` (EN_CAMINO) a `>= 3` (EN_PREP) en `cancelar_pedido`
- **Frontend**: Verificar que el botón "Cancelar" en la UI de pedidos respete la nueva regla (opcional, el backend ya rechazará la operación)
