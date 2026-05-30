## Why

Actualmente, cuando un cliente crea un pedido desde el carrito, el stock se valida en el backend al avanzar a CONFIRMADO, pero el error se traga silenciosamente. El cliente no recibe feedback sobre productos sin stock — el pedido queda en PENDIENTE sin explicación. Además, productos con stock=0 o no disponibles siguen mostrando el botón "Agregar al carrito", generando fricción y pedidos inválidos.

## What Changes

1. **Pre-validación de stock en el checkout**: Antes de crear un pedido, el frontend consulta un nuevo endpoint que verifica stock disponible. Si hay insuficiencias, se muestra un modal que permite al cliente reducir cantidad o remover productos directamente desde el carrito.
2. **Productos sin stock no agregables**: En la grilla de productos, los productos con `disponible=false`, stock=0 (o con todas sus medidas sin stock) se muestran visualmente pero el botón "Agregar al carrito" aparece deshabilitado con indicación "Sin stock" / "No disponible".
3. **Propagación correcta del error de stock**: El auto-advance en la creación de pedidos DEJA de tragar la excepción de stock insuficiente. El frontend maneja el 409 mostrando el modal de advertencia con opciones de resolución.

## Capabilities

### New Capabilities
- `stock-pre-validation`: Endpoint y lógica para verificar disponibilidad de stock antes de crear un pedido, sin efectos secundarios.

### Modified Capabilities
<!-- No existing specs to modify. This change adds new behavior to existing
     cart/checkout and product listing flows without changing existing specs. -->

## Impact

- **Backend**: Nuevo endpoint `POST /pedidos/validar-stock`. Modificación del `POST /pedidos/` para propagar errores de stock en auto-advance.
- **Frontend/src/pages/Carrito.tsx**: Nuevo modal `StockWarningModal` + flujo de pre-validación antes de crear pedido.
- **Frontend/src/pages/ProductosCRUD.tsx**: Botón "Agregar al carrito" deshabilitado condicionalmente según stock/disponibilidad.
- **Frontend/src/api/pedidos.ts**: Nueva función `validarStock()`.
