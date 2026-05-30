## 1. Backend — Modelos: Ingrediente + ProductoIngrediente

- [x] 1.1 Agregar `precio_actual: Decimal = Field(default=0, sa_column=Column(Numeric(10,2)))` a `IngredienteBase` en `Ingrediente/models.py`
- [x] 1.2 Agregar `stock_actual: int = Field(default=0, ge=0)` a `IngredienteBase` en `Ingrediente/models.py`
- [x] 1.3 Agregar `cantidad: Decimal = Field(default=1, sa_column=Column(Numeric(10,2)))` a `ProductoIngrediente` en `producto_ingrediente.py`
- [x] 1.4 Verificar que `SQLModel.metadata.create_all()` genera las nuevas columnas al iniciar (syntax check passed)

## 2. Backend — Schemas de Ingrediente

- [x] 2.1 Actualizar `IngredienteCreate` en `Ingrediente/schemas.py`: agregar `precio_actual: Decimal = 0` y `stock_actual: int = 0` (opcionales, default 0)
- [x] 2.2 Actualizar `IngredienteUpdate` en `Ingrediente/schemas.py`: agregar `precio_actual: Optional[Decimal] = None` y `stock_actual: Optional[int] = None`
- [x] 2.3 Actualizar `IngredienteRead` en `Ingrediente/schemas.py`: agregar `precio_actual: Decimal` y `stock_actual: int`
- [x] 2.4 Crear schemas dedicados `IngredientePrecioUpdate(BaseModel)` y `IngredienteStockUpdate(BaseModel)` con validacion (precio >= 0, stock >= 0)

## 3. Backend — Schemas de ProductoIngrediente

- [x] 3.1 Actualizar `IngredienteAsignado` en `Producto/schemas.py`: agregar `cantidad: Decimal = 1` (opcional, default 1)
- [x] 3.2 Actualizar `ProductoIngredienteRead` en `Producto/schemas.py`: agregar `cantidad: Decimal`

## 4. Backend — Service de Ingrediente

- [x] 4.1 En `IngredienteService`, implementar `actualizar_precio(session, ingrediente_id, precio: Decimal)`: validar existencia, actualizar precio, llamar a `recalcular_precio_productos_afectados()`
- [x] 4.2 En `IngredienteService`, implementar `actualizar_stock(session, ingrediente_id, stock: int)`: validar existencia, actualizar stock_actual
- [x] 4.3 En `IngredienteService`, modificar `update()` para que si `data.precio_actual` fue enviado, dispare recalculo de precios de productos afectados

## 5. Backend — Service de Producto: recalculo de precio

- [x] 5.1 En `ProductoService`, implementar `_recalcular_precio_producto(session, producto_id)`: calcular `SUM(ingrediente.precio_actual * pi.cantidad)` y actualizar `producto.precio_base`
- [x] 5.2 En `ProductoService`, implementar `recalcular_precio_productos_afectados(session, ingrediente_id)`: obtener todos los productos que usan ese ingrediente y llamar a `_recalcular_precio_producto()` para cada uno
- [x] 5.3 Modificar `ProductoService.create()`: si el producto tiene ingredientes en el payload, calcular `precio_base` automaticamente
- [x] 5.4 Modificar `ProductoService.update()`: si cambian los ingredientes del producto, recalcular `precio_base`
- [x] 5.5 En `ProductoService`, al agregar/quitar ingrediente (metodos existentes), recalcular `precio_base` del producto

## 6. Backend — Service de Pedido: descuento de stock de ingredientes

- [x] 6.1 En `PedidoService.avanzar_estado()`, al transicionar a CONFIRMADO: para cada `DetallePedido`, iterar `producto.ingredientes` y descontar `Ingrediente.stock_actual -= pi.cantidad * detalle.cantidad`
- [x] 6.2 Validar stock suficiente antes de descontar: si algun ingrediente tiene `stock_actual < (pi.cantidad * detalle.cantidad)`, retornar 409 con detalle del ingrediente faltante
- [x] 6.3 Verificar que el descuento ocurre dentro de la misma transaccion UoW (rollback si falla a mitad)

## 7. Backend — Router de Ingrediente

- [x] 7.1 Agregar endpoint `PATCH /ingredientes/{id}/precio` (requiere ADMIN, STOCK): recibe `IngredientePrecioUpdate`, llama a `IngredienteService.actualizar_precio()`
- [x] 7.2 Agregar endpoint `PATCH /ingredientes/{id}/stock` (requiere ADMIN, STOCK): recibe `IngredienteStockUpdate`, llama a `IngredienteService.actualizar_stock()`
- [x] 7.3 Verificar que `GET /ingredientes/` y `GET /ingredientes/{id}` incluyen `precio_actual` y `stock_actual` en la respuesta

## 8. Backend — Seed data

- [x] 8.1 Actualizar `seed.py`: agregar `precio_actual` y `stock_actual` a los 30 ingredientes existentes (ej: Pan de hamburguesa $50/stock500, Carne de res $200/stock200, Queso cheddar $80/stock300, etc.)
- [x] 8.2 Actualizar `seed.py`: agregar `cantidad` a las asociaciones `ProductoIngrediente` existentes en los productos de ejemplo (ej: para Hamburguesa Clasica: Pan=1, Carne=1, Queso=2, Lechuga=0.5, Tomate=0.5)
- [x] 8.3 Verificar que al ejecutar seed, los `precio_base` de productos se calculan correctamente desde ingredientes

## 9. Frontend — API types

- [x] 9.1 Actualizar interface `Ingrediente` en `api/ingredientes.ts`: agregar `precio_actual: number` y `stock_actual: number`
- [x] 9.2 Actualizar interface `IngredienteCreate` en `api/ingredientes.ts`: agregar `precio_actual?: number` y `stock_actual?: number`
- [x] 9.3 Actualizar interface `IngredienteUpdate` en `api/ingredientes.ts`: agregar `precio_actual?: number | null` y `stock_actual?: number | null`
- [x] 9.4 Agregar metodos `ingredientesApi.updatePrecio(id, precio)` y `ingredientesApi.updateStock(id, stock)` en `api/ingredientes.ts`
- [x] 9.5 Actualizar interface `ProductoIngredienteRead` en `api/productos.ts`: agregar `cantidad: number`

## 10. Frontend — IngredientesCRUD

- [x] 10.1 Agregar columnas "Precio" y "Stock" en la tabla de ingredientes, con formato moneda y numero
- [x] 10.2 En el formulario de crear/editar ingrediente, agregar inputs para `precio_actual` (number step=0.01) y `stock_actual` (number, integer)
- [x] 10.3 Agregar modo "Ajustar Stock" inline: boton por fila que abre input para nuevo valor de stock + boton "Guardar" (evita abrir formulario completo solo para cambiar stock)
- [x] 10.4 Agregar modo "Actualizar Precio" inline: similar al de stock, input para nuevo precio + guardar
- [x] 10.5 Al crear ingrediente, enviar `precio_actual` y `stock_actual` en el POST
- [x] 10.6 Al editar ingrediente, permitir modificar precio y stock (o usar los modos inline)

## 11. Frontend — ProductosCRUD: precio calculado

- [x] 11.1 En la tabla de productos, si el producto tiene ingredientes, mostrar `precio_base` con indicador "(calc)" al lado
- [x] 11.2 En el formulario de edicion de producto con ingredientes, hacer el campo `precio_base` read-only con texto "Calculado desde ingredientes"
- [x] 11.3 En el formulario de edicion de producto SIN ingredientes, mantener `precio_base` editable como hoy

## 12. Frontend — ProductosCRUD: cantidad por ingrediente

- [x] 12.1 En la seccion de "Ingredientes" del formulario de producto, agregar columna "Cantidad" con input number step=0.1
- [x] 12.2 Al agregar un ingrediente al producto, incluir `cantidad` en el payload (default 1)
- [x] 12.3 Al editar `cantidad` de un ingrediente existente, enviar PATCH con la nueva cantidad
- [x] 12.4 Mostrar el costo parcial de cada ingrediente en la tabla: `precio_actual * cantidad` con formato moneda
- [x] 12.5 Mostrar el total calculado (suma de costos parciales) actualizado en tiempo real mientras se editan ingredientes

## 13. Verificacion final

- [x] 13.1 Verificar que al crear un producto con ingredientes, el `precio_base` se calcula correctamente
- [x] 13.2 Verificar que al cambiar `precio_actual` de un ingrediente, se recalculan todos los productos afectados
- [x] 13.3 Verificar que al confirmar un pedido, se descuenta stock de ingredientes
- [x] 13.4 Verificar que el stock insuficiente de ingredientes retorna 409 y NO descuenta nada
- [x] 13.5 Verificar que productos con medidas NO se ven afectados por el calculo automatico
- [x] 13.6 Verificar que productos sin ingredientes mantienen precio_base manual
