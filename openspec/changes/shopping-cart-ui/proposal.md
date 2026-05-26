## Why

El sistema necesita un carrito de compras para que los usuarios (CLIENT, PEDIDOS, STOCK, ADMIN) puedan agregar productos y gestionar cantidades antes de realizar un pedido. Actualmente no hay forma de armar un pedido desde el frontend.

## What Changes

1. **Nueva página Carrito**: Ruta `/carrito` con un resumen de productos seleccionados, cantidades editables, precios por línea y total general.
2. **Botón "Agregar al carrito"**: En la página de Productos, cada producto tendrá un botón para agregarlo al carrito.
3. **Control de cantidades**: En el carrito, cada producto tendrá controles para aumentar/disminuir cantidad (mínimo 1) y un botón para eliminar el producto del carrito.
4. **Cálculo de total**: Sumatoria automática del precio total de todos los productos en el carrito.
5. **Botón "Realizar pedido"**: Presente en el carrito (funcionalidad en un change futuro).
6. **Default page**: La página de Productos pasa a ser la landing page por defecto para todos los roles (reemplaza a Categorías como首页).
7. **Persistencia del carrito**: El carrito se mantiene en localStorage para que sobreviva a recargas de página. No hay backend de carrito — es purely frontend state.

## Capabilities

### New Capabilities
- `shopping-cart`: Componente de carrito de compras con lista de productos, control de cantidades (min 1, incrementar, decrementar, eliminar), cálculo de total por línea y total general, y botón "Realizar pedido".

### Modified Capabilities
<!-- Sin cambios en specs existentes — todo es frontend nuevo -->

## Impact

- **Frontend**: Nueva página `Carrito.tsx` en `src/pages/`.
- **Frontend**: Modificación de `ProductosCRUD.tsx` para agregar botón "Agregar al carrito" en cada fila de producto, visible para todos los roles.
- **Frontend**: Modificación de `App.tsx` para agregar ruta `/carrito`, link de navegación al carrito, y cambiar landing page default a `/productos`.
- **Backend**: Sin cambios (el carrito es frontend-only con localStorage).
