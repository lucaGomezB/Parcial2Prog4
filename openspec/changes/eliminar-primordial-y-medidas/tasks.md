## 1. Backend — Modelos: Categoria, ProductoMedida, DetallePedido

- [x] 1.1 Eliminar campo `es_primordial` de `CategoriaBase` en `Categoria/models.py`
- [x] 1.2 Eliminar clase `ProductoMedida` completa en `Producto/models.py`
- [x] 1.3 Eliminar relacion `medidas: List[ProductoMedida]` de `Producto` en `Producto/models.py`
- [x] 1.4 Eliminar campo `medida_snapshot` de `DetallePedido` en `DetallePedido/models.py` (dejar comentario de que existe para datos historicos)

## 2. Backend — Schemas: Producto, Categoria, Pedido

- [x] 2.1 Eliminar `ProductoMedidaCreate` y `ProductoMedidaRead` de `Producto/schemas.py`
- [x] 2.2 Eliminar campo `medidas` de `ProductoCreate` en `Producto/schemas.py`
- [x] 2.3 Eliminar campo `medidas` de `ProductoRead` en `Producto/schemas.py`
- [x] 2.4 Eliminar campo `es_primordial` de `CategoriaCreate` en `Categoria/schemas.py`
- [x] 2.5 Eliminar campo `es_primordial` de `CategoriaUpdate` en `Categoria/schemas.py`
- [x] 2.6 Eliminar campo `es_primordial` de `CategoriaRead` en `Categoria/schemas.py`
- [x] 2.7 Eliminar campo `medida_id` de `DetallePedidoInput` en `Pedido/schemas.py`
- [x] 2.8 Eliminar campo `medida_snapshot` de `DetallePedidoRead` en `Pedido/schemas.py`
- [x] 2.9 Eliminar campo `medida_id` de `ValidarStockDetalleInput` en `Pedido/schemas.py`
- [x] 2.10 Eliminar campos `medida_id` y `medida` de `ValidarStockDetalleResponse` en `Pedido/schemas.py`

## 3. Backend — ProductoService: eliminar logica de medidas

- [x] 3.1 Eliminar import de `ProductoMedida` en `Producto/service.py`
- [x] 3.2 Eliminar import de `ProductoMedidaCreate` en `Producto/service.py`
- [x] 3.3 Eliminar metodo `_categoria_tiene_ancestro_primordial()` en `Producto/service.py`
- [x] 3.4 Eliminar validacion de `tiene_cat_primordial` en `ProductoService.create()` — ahora TODOS los productos requieren ingredientes
- [x] 3.5 Simplificar condicion de stock en create: eliminar `and not data.medidas` — solo verificar `db_producto.stock_cantidad == 0`
- [x] 3.6 Eliminar bloque `if data.medidas:` en create (creacion de instancias ProductoMedida)
- [x] 3.7 Eliminar early return `if db_producto.medidas:` en `_recalcular_precio_producto()` — ahora se calcula siempre que tenga ingredientes
- [x] 3.8 Eliminar variable `tiene_medidas` y su logica en `ProductoService.update()`
- [x] 3.9 Simplificar condicional `if not tiene_medidas:` en update — aplicar reglas de stock siempre
- [x] 3.10 Eliminar los 4 metodos del CRUD de medidas: `listar_medidas`, `crear_medida`, `actualizar_medida`, `eliminar_medida`

## 4. Backend — PedidoService: eliminar logica de medidas

- [x] 4.1 Eliminar import de `ProductoMedida` en `Pedido/service.py`
- [x] 4.2 Eliminar bloque `if det.medida_id is not None:` en `create()` (validacion de medida + snapshot)
- [x] 4.3 Eliminar rama `if det.medida_id is not None:` en `validar_stock_items()` (validacion contra ProductoMedida)
- [x] 4.4 Eliminar campo `medida_id` de `ValidarStockDetalleResponse` en `validar_stock_items()`
- [x] 4.5 Eliminar bloque `if det.medida_snapshot:` en `avanzar_estado()` (stock contra ProductoMedida por nombre)
- [x] 4.6 Eliminar bloque `if det.medida_snapshot:` en `avanzar_estado()` CONFIRMADO (descuento de ProductoMedida.stock)
- [x] 4.7 Simplificar metodo `avanzar_estado()` para que siempre descuente de `Producto.stock_cantidad` (o del sistema de ingredientes)

## 5. Backend — Router: eliminar endpoints de medidas

- [x] 5.1 Eliminar imports de `ProductoMedidaRead`, `ProductoMedidaCreate` en `Producto/router.py`
- [x] 5.2 Eliminar los 4 endpoints de medidas en `Producto/router.py`: GET/POST/PATCH/DELETE /productos/{id}/medidas

## 6. Backend — Seed

- [x] 6.1 Eliminar import de `ProductoMedida` en `seed.py`
- [x] 6.2 Eliminar `es_primordial` de los tuples en `CATEGORIAS_SEED` (cambiar a False o quitar)
- [x] 6.3 Actualizar desempaquetado de `CATEGORIAS_SEED` para no incluir es_primordial
- [x] 6.4 Eliminar bloque de creacion de medidas en seed (productos con Coca Cola, Pizza, Tarta)

## 7. Frontend — API types

- [x] 7.1 Eliminar interfaces `ProductoMedida` y `ProductoMedidaCreate` de `api/productos.ts`
- [x] 7.2 Eliminar campo `medidas` de interface `Producto` en `api/productos.ts`
- [x] 7.3 Eliminar campo `medidas` de interface `ProductoCreate` en `api/productos.ts`
- [x] 7.4 Eliminar funciones `getMedidas`, `createMedida`, `updateMedida`, `deleteMedida` de `api/productos.ts`
- [x] 7.5 Eliminar campo `medida_snapshot` de interface `DetallePedido` en `api/pedidos.ts`
- [x] 7.6 Eliminar campo `medida` de `StockInsuficienteDetalle` en `api/pedidos.ts`
- [x] 7.7 Eliminar campo `medida_id` de `ValidarStockDetalleInput` en `api/pedidos.ts`
- [x] 7.8 Eliminar campos `medida` y `medida_id` de `ValidarStockDetalle` en `api/pedidos.ts`
- [x] 7.9 Eliminar campo `medida_id` del type de create order detail en `api/pedidos.ts`
- [x] 7.10 Eliminar campo `es_primordial` de interfaces `Categoria`, `CategoriaCreate`, `CategoriaUpdate`, `CategoriaTree` en `api/categorias.ts`

## 8. Frontend — utils/carrito.ts

- [x] 8.1 Eliminar `medidaId` y `medidaNombre` de interface `CarritoItem`
- [x] 8.2 Eliminar parametros `medidaId` y `medidaNombre` de funcion `addToCart()`
- [x] 8.3 Eliminar filtro por `medidaId` en `addToCart()` (key unico por productoId)
- [x] 8.4 Eliminar `medidaId` del objeto pusheado en `addToCart()`
- [x] 8.5 Eliminar parametro `medidaId` de `removeFromCart()` y `updateCantidad()`
- [x] 8.6 Eliminar filtros por `medidaId` en `removeFromCart()` y `updateCantidad()`

## 9. Frontend — CategoriasCRUD

- [x] 9.1 Eliminar badge "Primordial" de la tabla de categorias
- [x] 9.2 Eliminar `es_primordial: false` del initial form state
- [x] 9.3 Eliminar variable `parentIsPrimordial` y su logica
- [x] 9.4 Eliminar `es_primordial` de handleEdit, handleCreate, handleCloseForm
- [x] 9.5 Eliminar bloque del checkbox "Es primordial" en el formulario

## 10. Frontend — ProductosCRUD: MedidaSelectorModal

- [x] 10.1 Eliminar import de `ProductoMedida` de `api/productos`
- [x] 10.2 Eliminar funcion completa `MedidaSelectorModal()` (~110 lineas)
- [x] 10.3 Eliminar estados `newMedida`, `existingMedidas`, `medidaModalProducto`
- [x] 10.4 Eliminar condicion `if prod.medidas && prod.medidas.length > 0` en handleAddToCart — siempre agregar directo
- [x] 10.5 Eliminar funcion `handleMedidaConfirm`
- [x] 10.6 Eliminar effect de carga de existingMedidas
- [x] 10.7 Eliminar variable `hasPrimordialCategory` y `catAncestryMap`
- [x] 10.8 Eliminar variable `tieneMedidas`
- [x] 10.9 Eliminar render de `<MedidaSelectorModal>` en el JSX

## 11. Frontend — ProductosCRUD: Stock Edit Mode simplificado

- [x] 11.1 Eliminar rama `existingMedidas.length > 0` en Stock Edit — mantener solo editor de stock_cantidad
- [x] 11.2 Simplificar `stockDisabled` a solo depender del estado de edicion
- [x] 11.3 Eliminar tooltip "El stock se gestiona a traves de las medidas/porciones"

## 12. Frontend — ProductosCRUD: Formulario

- [x] 12.1 Eliminar bloque de medidas en create form (inputs de nombre/precio/stock por medida)
- [x] 12.2 Eliminar condicion `tieneMedidas && hasPrimordialCategory` en deshabilitado de ingredientes
- [x] 12.3 Eliminar condicion `hasPrimordialCategory` que mostraba seccion de medidas
- [x] 12.4 Eliminar bloque `if (existingMedidas.length > 0)` en handleSubmit

## 13. Frontend — ProductosCRUD: Display en tabla

- [x] 13.1 Simplificar display de precio: siempre mostrar `precio_base` (eliminar logica de rango de medidas)
- [x] 13.2 Simplificar display de stock: siempre mostrar `stock_cantidad` (eliminar suma de medidas)
- [x] 13.3 Simplificar logica de disponible: usar campo `disponible` directo
- [x] 13.4 Simplificar boton "Agregar al carrito": usar stock_cantidad simple

## 14. Frontend — Carrito.tsx

- [x] 14.1 Simplificar keys de items (eliminar `${medidaId}` del key compuesto)
- [x] 14.2 Eliminar parametro `medidaId` de handleRemove, handleIncrement, handleDecrement
- [x] 14.3 Eliminar `medida_id` de llamadas a validar stock y crear pedido
- [x] 14.4 Eliminar logica de `medidaIdStr` en handleStockAdjust
- [x] 14.5 Eliminar display de medidaNombre en items del carrito

## 15. Frontend — PedidosPage.tsx

- [x] 15.1 Eliminar columna "Medida" del DetallesPopup
- [x] 15.2 Eliminar columna "Medida" del StockWarning

## 16. Verificacion final

- [x] 16.1 Verificar que el backend compila sin errores (imports, referencias a ProductoMedida)
- [x] 16.2 Verificar que el frontend compila sin errores TypeScript
- [x] 16.3 Verificar que CategoriasCRUD funciona sin es_primordial
- [x] 16.4 Verificar que ProductosCRUD carga y muestra productos sin medidas
- [x] 16.5 Verificar que Carrito funciona sin logica de medidas
- [x] 16.6 Verificar que crear/confirmar pedidos funciona sin medida_id ni medida_snapshot
- [x] 16.7 Verificar que seed ejecuta sin errores
