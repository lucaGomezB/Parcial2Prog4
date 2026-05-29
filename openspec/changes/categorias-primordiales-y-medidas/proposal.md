## Why

Actualmente cada variante de un producto (Coca Cola 250ml, 500ml, 1L) debe registrarse como un producto separado, duplicando datos y haciendo imposible agruparlas lógicamente. Esto también impide que el cliente elija tamaño/porción al armar su pedido. Se necesita un sistema de "medidas" para productos en categorías primordiales (Bebidas, Tartas, Pizzas) que permita definir múltiples presentaciones con precio y stock propio por medida.

## What Changes

- **Nuevo campo `es_primordial` en Categoria**: flag que indica que los productos de esa categoría pueden tener medidas
- **Nueva tabla `ProductoMedida`**: cada producto puede tener N medidas (nombre, precio propio, stock propio, orden)
- **Regla de negocio**: si un producto tiene medidas, `precio_base` y `stock_cantidad` del producto se ignoran; se usa precio y stock de cada medida
- **`disponible` del producto**: verdadero si al menos una medida tiene stock > 0
- **Frontend Producto CRUD**: si el producto tiene al menos una categoría primordial, muestra sección "Medidas" en el formulario (agregar/quitar medidas con nombre, precio, stock)
- **Frontend Stock Editor**: si el producto tiene medidas, edita stock por medida (no el stock general)
- **Frontend Carrito**: al agregar producto con medidas, muestra selector de medida antes de agregar
- **DetallePedido.medida_snapshot**: nuevo campo para registrar qué medida se eligió al hacer el pedido
- **Seed**: actualizado con categorías primordiales y productos con medidas de ejemplo

## Capabilities

### New Capabilities
- `producto-medidas`: Gestión de medidas por producto (crear, listar, actualizar, eliminar)
- `pedido-medidas`: Selección y registro de medidas en el flujo de pedido (carrito → snapshot en DetallePedido)

### Modified Capabilities
- `categorias`: Nuevo campo `es_primordial` para marcar categorías que habilitan medidas
- `productos`: Los productos con medidas usan precio/stock por medida en lugar de los campos directos
- `stock`: El editor de stock debe mostrar stock por medida cuando corresponda

## Impact

- **Backend**: Nueva tabla `ProductoMedida`, nuevo campo `Categoria.es_primordial`, nuevo campo `DetallePedido.medida_snapshot`, nuevos endpoints CRUD para medidas
- **Frontend**: Modificar `ProductosCRUD.tsx`, `Carrito.tsx`, `carrito.ts`, crear componentes de selector de medidas
- **Seed**: Actualizar `seed.py` con datos de ejemplo
- **API**: Nuevos endpoints `/productos/{id}/medidas/`
- **Stock**: Lógica de descuento de stock debe apuntar a la medida, no al producto
