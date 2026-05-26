## Why

El ERD v5 especifica **DECIMAL(10,2)** para todos los campos monetarios (subtotal, descuento, costo_envio, total, precio_snapshot, subtotal_snap, transaction_amount). Actualmente estos campos están tipados como `float` en los modelos y schemas, lo que puede causar errores de redondeo acumulativos en operaciones financieras. Producto.precio_base ya usa `Decimal(Numeric(10,2))` correctamente — hay que alinear el resto.

Adicionalmente, el ERD v5 especifica `CHAR(60)` para `password_hash` y `CHAR(64)` para `token_hash`, pero en la práctica PostgreSQL maneja `VARCHAR` de forma más eficiente para estos casos y no hay diferencia funcional (bcrypt y SHA-256 siempre producen strings de longitud fija). Se confirma mantener `VARCHAR` (vía `max_length`) como está actualmente.

## What Changes

- Cambiar todos los campos `float` de Pedido, DetallePedido y Pago a `Decimal` con `Numeric(precision=10, scale=2)` en los modelos SQLModel
- Actualizar los schemas Pydantic correspondientes para usar `Decimal` en vez de `float`
- Confirmar que `CHAR` → `VARCHAR` en `password_hash` y `token_hash` es correcto (se mantiene `max_length`)
- Confirmar que `SoftDeleteModel` en Ingrediente se conserva (defensivo, no perjudica)
- Confirmar que los campos extra (`tiempo_prep_min`, `orden_display`, `es_principal`/`orden` en ProductoIngrediente) se mantienen
- NO hay cambios de comportamiento — solo precisión de tipos

## Capabilities

### New Capabilities
- `type-precision`: Precisión DECIMAL(10,2) en campos monetarios y confirmación de tipos VARCHAR vs CHAR. Cubre Pedido (subtotal, descuento, costo_envio, total), DetallePedido (precio_snapshot, subtotal_snap), Pago (transaction_amount), y decisión de arquitectura sobre CHAR/VARCHAR.

### Modified Capabilities
_(No existing specs to modify)_

## Impact

- **Backend/modules/VentasPagosTrazabilidad/Pedido/models.py**: subtotal, descuento, costo_envio, total: `float` → `Decimal(Numeric(10,2))`
- **Backend/modules/VentasPagosTrazabilidad/Pedido/schemas.py**: PedidoCreate, PedidoUpdate, PedidoRead: `float` → `Decimal`
- **Backend/modules/VentasPagosTrazabilidad/DetallePedido/models.py**: precio_snapshot, subtotal_snap: `float` → `Decimal(Numeric(10,2))`
- **Backend/modules/VentasPagosTrazabilidad/DetallePedido/schemas.py**: DetallePedidoCreate, DetallePedidoRead: `float` → `Decimal`
- **Backend/modules/VentasPagosTrazabilidad/Pago/models.py**: transaction_amount: `float` → `Decimal(Numeric(10,2))`
- **Sin cambios**: password_hash (VARCHAR ok), token_hash (VARCHAR ok), SoftDeleteModel en Ingrediente (se mantiene), campos extra (se mantienen)
