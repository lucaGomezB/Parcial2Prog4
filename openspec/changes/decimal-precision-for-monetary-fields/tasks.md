## 1. Pedido models + schemas

- [x] 1.1 Cambiar `subtotal`, `descuento`, `costo_envio`, `total` en `PedidoBase` de `float` a `Decimal` con `Numeric(precision=10, scale=2)`
- [x] 1.2 Actualizar `PedidoCreate`, `PedidoRead` schemas: `float` → `Decimal`

## 2. DetallePedido models + schemas

- [x] 2.1 Cambiar `precio_snapshot`, `subtotal_snap` en `DetallePedido` de `float` a `Decimal` con `Numeric(precision=10, scale=2)`
- [x] 2.2 Actualizar `DetallePedidoCreate`, `DetallePedidoRead` schemas: `float` → `Decimal`

## 3. Pago models

- [x] 3.1 Cambiar `transaction_amount` en `Pago` de `float` a `Decimal` con `Numeric(precision=10, scale=2)`

## 4. Decisiones de diseño (sin cambios de código)

- [x] 4.1 Confirmar que `password_hash` (max_length=60) y `token_hash` (max_length=64) se mantienen como VARCHAR (no migrar a CHAR)
- [x] 4.2 Confirmar que `SoftDeleteModel` en Ingrediente se conserva
- [x] 4.3 Confirmar que `tiempo_prep_min` (Producto), `orden_display` (Categoria), `es_principal`/`orden` (ProductoIngrediente) se mantienen

## 5. Verificación

- [x] 5.1 Verificar que todos los imports de `Decimal` y `Numeric` sean correctos
- [x] 5.2 Verificar que `PedidoService.create()` calcula el total con `Decimal` (subtotal - descuento + costo_envio)
- [x] 5.3 Verificar que la API serializa correctamente los valores Decimal a JSON
