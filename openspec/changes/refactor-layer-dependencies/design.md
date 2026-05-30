## Context

El backend está organizado en módulos con router/service/uow/repository/models/schemas, pero hay fugas de dependencia:

- **Router** de Pedidos importa `VentasPagosTrazabilidadUnitOfWork`, `DetallePedido.models`, `HistorialEstadoPedido.models` y `Usuario.models` — opera con UoW y hace queries SQL directas en `actualizar_detalle()` y `avanzar()`.
- **Schemas** de Producto heredan de `ProductoBase` que es un `SQLModel` — acopla la capa de DTOs a la capa de persistencia.
- **Service** de Pedidos importa models de `CatalogoDeProductos` — acoplamiento cross-context que se deja para otro cambio.

## Goals / Non-Goals

**Goals:**
- Router de Pedidos solo depende de Service, Schemas, y dependencias de infraestructura (database, auth)
- `actualizar_detalle()` vive en el Service, no en el Router
- El endpoint `avanzar()` no hace queries directas al historial
- Schemas de Producto no heredan de modelos SQLModel

**Non-Goals:**
- No se cambia la API pública de los endpoints (requests/responses)
- No se toca el acoplamiento cross-context PedidoService → ProductoMedida
- No se agregan interfaces/ports (reservado para otro cambio)

## Decisions

### 1. `actualizar_detalle()` en Service
- **Decisión**: Crear `PedidoService.actualizar_detalle(session, pedido_id, producto_id, cantidad)` que contenga toda la lógica (validación de estado PENDIENTE, update/delete del detalle, recálculo de total, commit).
- **Por qué**: El router no debería manejar transacciones ni lógica de negocio. El service es responsable de coordinar el UoW.
- **Firma**: `actualizar_detalle(session, pedido_id, producto_id, cantidad: int) -> Pedido`
- **Comportamiento**: `cantidad=0` elimina el detalle. `cantidad>0` actualiza cantidad y subtotal_snap. Recalcula subtotal y total del pedido. Commitea con UoW.

### 2. Historial en `avanzar()`
- **Decisión**: `PedidoService.avanzar_estado()` ya registra en `HistorialEstadoPedido`. Modificar el método para que devuelva una tupla `(pedido, estado_anterior)` o un objeto con ambos valores, eliminando la necesidad de que el router consulte el historial.
- **Alternativa**: Dejar el router consultando el historial. Se descartó porque viola la separación de capas.
- **Implementación**: Opción más simple — cambiar el método para que registre el historial ANTES de actualizar el pedido, así podemos capturar `estado_anterior` desde el `db_pedido.estado_codigo` antes del cambio. Devolver `(pedido, estado_anterior)` como tupla.

### 3. Schemas de Producto
- **Decisión**: Duplicar campos en `ProductoCreate` y `ProductoRead` en vez de heredar de `ProductoBase` (SQLModel).
- **Por qué**: Los schemas son DTOs de la API, no deberían acoplarse a la estructura de la DB. Desheredar rompe el acoplamiento.
- **Riesgo**: Divergencia futura si se agrega un campo al modelo y no al schema. → **Mitigación**: Confiar en que las reviews lo detecten.

## Risks / Trade-offs

- **[Riesgo] Regression en actualizar_detalle**: Al mover la lógica, algún detalle de manejo de transacciones podría diferir. → **Mitigación**: Probar manualmente los casos: cantidad>0, cantidad=0, pedido no PENDIENTE, detalle inexistente.
- **[Riesgo] Tupla como retorno rompe compatibilidad**: Si algún otro caller de `avanzar_estado()` espera solo un `Pedido`. → **Mitigación**: Verificar que solo el router de avance y el auto-advance del create llaman a este método. Ajustar ambos.
