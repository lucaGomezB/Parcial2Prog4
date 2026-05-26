## 1. Utilidad de carrito (localStorage)

- [x] 1.1 Crear `src/utils/carrito.ts` con funciones puras: `getCarrito()`, `addToCart(producto)`, `removeFromCart(productoId)`, `updateCantidad(productoId, cantidad)`, `getTotal()`, `getItemCount()`, `clearCarrito()`. Todas operan sobre `localStorage` key `"carrito"`.
- [x] 1.2 Definir interfaz `CarritoItem` exportada: `{ productoId: number; nombre: string; precio: number; cantidad: number }`

## 2. Página Carrito

- [x] 2.1 Crear `src/pages/Carrito.tsx` que lea el carrito desde localStorage y muestre una tabla con columnas: Producto, Precio Unitario, Cantidad (+/−), Total, Acciones (Quitar)
- [x] 2.2 Integrar controles +/− en cada fila: + incrementa, − decrementa (mínimo 1)
- [x] 2.3 Botón "Quitar" que elimina el producto del carrito usando `removeFromCart()`
- [x] 2.4 Mostrar total general abajo con `getTotal()`
- [x] 2.5 Botón "Realizar pedido" (placeholder, deshabilitado con mensaje "Próximamente")
- [x] 2.6 Estado vacío: mensaje "El carrito está vacío" con link a `/productos`

## 3. Botón "Agregar al carrito" en tabla de productos

- [x] 3.1 Agregar columna "Agregar" en la tabla de `ProductosCRUD.tsx` con un botón por fila que llame a `addToCart()`
- [x] 3.2 La columna es visible para TODOS los roles (incluido CLIENT)
- [x] 3.3 Feedback visual: botón cambia a "✓ Agregado" (verde) por 1.2s
- [x] 3.4 Ajustar `colSpan` de "Sin resultados" a 5/7/9 según el rol

## 4. Navegación + Landing page

- [x] 4.1 Ruta `/carrito` → `<Carrito />` agregada en App.tsx (ambos modos: client y no-client)
- [x] 4.2 Link "Carrito (N)" en el nav para TODOS los roles autenticados, con contador desde `getItemCount()`
- [x] 4.3 Landing page default ya era `/productos` (cambio previo)
- [x] 4.4 Headers y colSpan actualizados en tabla de productos
