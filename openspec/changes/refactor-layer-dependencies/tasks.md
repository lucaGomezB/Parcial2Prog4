## 1. Mover actualizar_detalle al Service

- [x] 1.1 Agregar `actualizar_detalle()` a `PedidoService` con la lógica completa (validación, update/delete, recálculo, commit)
- [x] 1.2 Simplificar `actualizar_detalle()` en el router: solo validar existencia del pedido + llamar al service
- [x] 1.3 Eliminar imports de `VentasPagosTrazabilidadUnitOfWork`, `DetallePedido` y `DetallePedidoUpdate` del router (si ya no se usan)
- [x] 1.4 Verificar que `PATCH /pedidos/{id}/detalles/{producto_id}` funciona igual (cantidad>0, cantidad=0, pedido no PENDIENTE)

## 2. Mover query de historial fuera del router

- [x] 2.1 Modificar `PedidoService.avanzar_estado()` para que devuelva `(pedido, estado_anterior)` en vez de solo `pedido`
- [x] 2.2 Actualizar el endpoint `avanzar()` en el router para usar el `estado_anterior` del service
- [x] 2.3 Actualizar el auto-advance en `POST /pedidos/` (router create) para manejar la nueva firma
- [x] 2.4 Eliminar import de `HistorialEstadoPedido.models` del router
- [x] 2.5 Verificar que `POST /pedidos/{id}/avanzar` devuelve exactamente la misma respuesta

## 3. Desacoplar schemas de Producto

- [x] 3.1 En `CatalogoDeProductos/Producto/schemas.py`, redefinir `ProductoCreate` con campos propios (sin heredar de `ProductoBase`)
- [x] 3.2 Verificar que `POST /productos/` y `PATCH /productos/{id}` siguen aceptando los mismos campos
- [x] 3.3 Verificar que `GET /productos/` y `GET /productos/{id}` devuelven los mismos campos
