## Why

El concepto de "categoria primordial" (`es_primordial`) y el sistema de "medidas/porciones" (`ProductoMedida`) asociado fue una abstraccion incorrecta desde el inicio. En un sistema de gestion de productos alimenticios, NO existe el concepto de que una categoria "habilite" un tipo de pricing distinto. Todos los productos se venden en una unidad base con un precio y stock unico.

El sistema de medidas (ej: Coca Cola 250ml/$1500, 500ml/$2500, 1L/$4000) deberia modelarse como productos separados, no como variantes de un mismo producto. La logica de `es_primordial` contaminaba:
- El modelo de Categoria (campo sin sentido semantico real)
- El modelo de Producto (relacion con ProductoMedida que complejifica todo)
- El servicio de Pedido (descuento de stock bifurcado: producto vs medida)
- El frontend completo (MedidaSelectorModal, stock editor por medida, precio range en tabla)
- La validacion de ingredientes (escape hatch que permitia productos sin ingredientes)

Ademas, con el cambio `ingredientes-con-stock-y-precio` recien implementado, el precio base del producto se calcula desde ingredientes. Tener un sistema paralelo de precios por medida es inconsistente y duplica logica.

**BREAKING**: Se elimina la tabla `productomedida`, la columna `es_primordial` en `categoria`, y la columna `medida_snapshot` en `detallepedido`.

## What Changes

- **Modelo Categoria**: Eliminar campo `es_primordial`
- **Modelo ProductoMedida**: Eliminar toda la clase (se dropea la tabla)
- **Producto.medidas**: Eliminar relacion
- **Schemas**: Eliminar ProductoMedidaCreate/Read, eliminar medidas de ProductoCreate/Read
- **Schemas Categoria**: Eliminar es_primordial de CategoriaCreate/Update/Read
- **DetallePedido.models**: Eliminar campo `medida_snapshot`
- **Schemas Pedido**: Eliminar `medida_id` y `medida_snapshot` de todos los schemas (DetallePedidoInput, DetallePedidoRead, ValidarStockDetalleInput/Response)
- **ProductoService**: Eliminar `_categoria_tiene_ancestro_primordial()`, toda la logica de medidas (crear/actualizar/eliminar medidas), simplificar validacion de stock/disponible, simplificar reglas de ingredientes (ahora TODOS los productos requieren ingredientes)
- **PedidoService**: Eliminar toda la logica de `medida_id`/`ProductoMedida` en create, validar_stock_items, avanzar_estado — todo producto usa `Producto.stock_cantidad` directamente
- **Router Producto**: Eliminar los 4 endpoints de medidas (GET/POST/PATCH/DELETE)
- **Router Categoria**: Eliminar referencias a es_primordial
- **Seed**: Eliminar es_primordial de categorias, eliminar creacion de ProductoMedida
- **Frontend api/**: Eliminar tipos ProductoMedida, eliminar funciones getMedidas/createMedida/updateMedida/deleteMedida, eliminar medida_id/medida_snapshot de tipos de pedido
- **Frontend CategoriasCRUD**: Eliminar checkbox "Es primordial", eliminar badge "Primordial"
- **Frontend ProductosCRUD**: Eliminar MedidaSelectorModal (~110 lineas), eliminar seccion de medidas en formulario, eliminar logica de precio range por medidas, simplificar display de stock
- **Frontend Carrito.tsx**: Eliminar toda logica de medidaId/medidaNombre, simplificar keys
- **Frontend PedidosPage.tsx**: Eliminar columna "Medida"
- **Frontend utils/carrito.ts**: Eliminar medidaId/medidaNombre de CarritoItem, eliminar parametros de funciones

## Capabilities

### Removed Capabilities
- `producto-medidas`: Sistema de medidas/porciones con precio y stock propio. Se elimina completamente.
- `pedido-medidas`: Descuento de stock bifurcado (producto vs medida) al confirmar pedidos. Se simplifica a un solo flujo.

### Modified Capabilities
- `product-management`: Se eliminan campos `medidas` de los schemas de producto. Se elimina toda la logica de CRUD de medidas. El precio y stock son siempre a nivel producto.
- `category-management`: Se elimina campo `es_primordial`. Las categorias dejan de tener un rol en el pricing del producto.
- `pedido-management`: Se elimina `medida_id` y `medida_snapshot` de todos los schemas de pedido. El descuento de stock es siempre sobre `Producto.stock_cantidad`.
- `ingredient-inventory`: Se elimina la excepcion de ingredientes para categorias primordiales. TODOS los productos requieren ingredientes ahora.
- `product-cost-calculation`: Se elimina el early return para productos con medidas. Ahora el precio se calcula desde ingredientes para TODOS los productos que tengan ingredientes.

## Impact

- **Database**: Se pierde la tabla `productomedica` y las columnas `es_primordial` (categoria) y `medida_snapshot` (detallepedido). Datos historicos en `medida_snapshot` se pierden (campos NULL).
- **Backend**: ~250 lineas eliminadas entre modelos, schemas, services, routers
- **Frontend**: ~350 lineas eliminadas entre tipos, componentes, utilidades
- **Carrito localStorage**: Items en carrito con `medidaId`/`medidaNombre` quedan obsoletos (el schema del item se simplifica)
