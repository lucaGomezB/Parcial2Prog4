## Why

El backend tiene tres violaciones al principio de capas con dependencia unidireccional: (1) el router de Pedidos opera directamente con UoW, Models y queries SQL, bypasseando el Service; (2) schemas heredan de modelos SQLModel creando acoplamiento; (3) el service de VentasPagos importa models de CatalogoDeProductos (cross-context). Las primeras dos son fáciles de corregir y mejoran la mantenibilidad sin riesgo. La tercera se deja para otro cambio por requerir una refactorización más profunda (Port & Adapter).

## What Changes

1. **Mover `actualizar_detalle()` del router al Service**: Toda la lógica de update/delete de detalle, recálculo de subtotal/total, y commit pasa a `PedidoService.actualizar_detalle()`. El router solo valida permisos y llama al service.
2. **Mover query de historial del endpoint `avanzar()` al Service**: El `avanzar_estado()` ya registra el historial; que también devuelva el estado anterior para eliminar la query directa en el router.
3. **Desacoplar schemas de Producto de los modelos SQLModel**: Separar `ProductoCreate` y `ProductoRead` de la herencia de `ProductoBase` (SQLModel), definiendo campos duplicados pero independientes.
4. **NO se toca** el acoplamiento cross-context (PedidoService → ProductoMedida). Queda pendiente.

## Capabilities

### New Capabilities
<!-- No new capabilities -->

### Modified Capabilities
<!-- Internal refactor only, no spec-level behavior changes -->
- `pedido-management`: Refactor interno de responsabilidades entre router/service
- `producto-management`: Refactor interno de schemas para eliminar herencia de modelos

## Impact

- **Backend/.../Pedido/router.py**: Eliminar imports de UoW, DetallePedido.models, HistorialEstadoPedido.models. Simplificar `actualizar_detalle()` y `avanzar()`.
- **Backend/.../Pedido/service.py**: Agregar `actualizar_detalle()` con la lógica movida del router. Modificar `avanzar_estado()` para devolver estado anterior.
- **Backend/.../Pedido/schemas.py**: Agregar schema `PedidoAvanzarResponse` actualizado si es necesario.
- **Backend/.../Producto/schemas.py**: Separar `ProductoCreate` y `ProductoRead` de `ProductoBase`.
- **No breaking**: Los endpoints mantienen exactamente la misma API pública. Solo cambia la organización interna.
