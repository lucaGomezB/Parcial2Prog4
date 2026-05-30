## Why

Currently, ingredients are purely cualitativos: solo tienen nombre, descripcion y flag de alergeno. El precio y stock se manejan **a nivel producto** de forma manual, sin relacion alguna con los ingredientes que lo componen. Para un negocio de productos alimenticios, el costo real del producto ES la suma de sus ingredientes. Sin esta relacion:

- No hay forma de calcular el precio base de un producto a partir de sus insumos
- Cuando cambia el precio de un ingrediente (ej: harina), hay que actualizar manualmente CADA producto que lo usa
- No hay control de stock por ingrediente → se puede vender un producto cuyos ingredientes no tienen stock
- La gestion de inventario esta desacoplada de la realidad del negocio

Este cambio resuelve eso: los ingredientes pasan a ser entidades con precio y stock propio, y el precio base del producto se calcula automaticamente como la suma de sus ingredientes multiplicados por la cantidad usada.

## What Changes

- **Ingrediente** gana campos `precio_actual: Decimal` y `stock_actual: int` — precio unitario vigente y stock disponible del insumo
- **ProductoIngrediente** gana campo `cantidad: Decimal` — que cantidad de ese ingrediente (en la unidad que corresponda) se usa en el producto
- El `precio_base` del producto se calcula automaticamente como `SUM(ingrediente.precio_actual * ProductoIngrediente.cantidad)` **cuando tiene ingredientes**. Si no tiene ingredientes, sigue siendo manual (ej: productos con medidas/porciones)
- Al confirmar un pedido (transicion a CONFIRMADO), se descuenta `Ingrediente.stock_actual` por cada ingrediente de cada producto en el pedido (multiplicado por la cantidad del detalle)
- **BREAKING**: El campo `precio_base` del producto deja de ser completamente manual cuando el producto tiene ingredientes. Se recalcula en cada operacion que afecte ingredientes.
- Seed data actualizada con precios y stocks de ingredientes
- Frontend: IngredientesCRUD ahora muestra y permite editar precio y stock
- Frontend: ProductosCRUD muestra `precio_calculado` vs `precio_base` y permite ajustar `cantidad` por ingrediente
- Frontend: Al agregar/quitar ingredientes de un producto, el precio se actualiza automaticamente

## Capabilities

### New Capabilities
- `ingredient-inventory`: Gestion de precio unitario y stock de cada ingrediente. Incluye endpoints para actualizar precio/stock, y la logica de descuento de stock al confirmar pedidos.
- `product-cost-calculation`: Calculo automatico del precio base del producto como suma de (precio_ingrediente * cantidad_usada). Recalculo en cada cambio de ingredientes del producto o cambio de precio de ingrediente.

### Modified Capabilities
- `product-management`: El precio_base del producto pasa de ser un campo 100% manual a ser calculado automaticamente desde ingredientes (cuando el producto los tiene). Se agrega visualizacion de precio calculado vs precio manual.
- `pedido-management`: Al confirmar un pedido (CONFIRMADO), ahora tambien descuenta stock de ingredientes, no solo stock de producto/medidas.

## Impact

- **Backend**: `Ingrediente/models.py` (nuevos campos), `ProductoIngrediente` model/table (nuevo campo cantidad), `Producto/service.py` (calculo automatico de precio), `Pedido/service.py` (descuento de stock de ingredientes), nuevos schemas
- **Frontend**: `IngredientesCRUD.tsx` (campos precio/stock), `ProductosCRUD.tsx` (cantidad por ingrediente, precio calculado), `api/ingredientes.ts` (tipos actualizados), `api/productos.ts` (tipos actualizados)
- **Database**: Migracion con nuevas columnas en `ingrediente` y `producto_ingrediente`
- **Seed**: Precios y stocks iniciales para los 30 ingredientes existentes
