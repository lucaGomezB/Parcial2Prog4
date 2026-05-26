## Context

El frontend actual lista productos en una tabla paginada con roles y permisos. No existe concepto de carrito de compras. Los usuarios no pueden armar pedidos desde la UI.

El carrito será puramente frontend, usando `localStorage` para persistencia. No requiere cambios en el backend.

## Goals / Non-Goals

**Goals:**
- Página `/carrito` con lista de productos agregados, cantidades editables (mínimo 1), precio por línea y total general
- Botón "Agregar al carrito" en cada fila de la tabla de productos (visible para todos los roles)
- Controles +/− para cantidad y botón "Eliminar" por producto
- Botón "Realizar pedido" (placeholder sin funcionalidad — próximo change)
- Productos como landing page default (`/productos` en vez de `/categorias`)
- Link de navegación al carrito en el header (visible para todos los roles autenticados)

**Non-Goals:**
- No backend de carrito (no hay endpoint de carrito)
- No persistencias en base de datos
- No cálculo de impuestos, descuentos o envío
- No checkout flow (el botón "Realizar pedido" está presente pero sin acción)

## Decisions

### 1. Estado del carrito en localStorage vs Context
- **Decisión**: `localStorage` + estado local en componente.
- **Por qué**: Simple, no requiere React Context ni provider. El carrito sobrevive a recargas. Se puede compartir entre páginas (Productos → Carrito) leyendo/escribiendo del mismo `localStorage` key.
- **Alternativa**: React Context — más elegante pero overkill para dos páginas. Si en el futuro se necesita acceso global desde muchos componentes, se puede migrar.

### 2. Tipo del carrito
```typescript
interface CarritoItem {
  productoId: number;
  nombre: string;
  precio: number;
  cantidad: number;
}
```

### 3. Ubicación de la lógica
- `src/utils/carrito.ts` → funciones puras: `getCarrito()`, `addToCart()`, `removeFromCart()`, `updateCantidad()`, `getTotal()`, `clearCarrito()`. Todas operan sobre localStorage.
- `src/pages/Carrito.tsx` → componente página que consume las funciones del utility.

### 4. Botón "Agregar al carrito" en tabla de productos
- Se agrega una columna "Agregar" al final de la tabla (después de Acciones) para todos los roles, incluido CLIENT (readOnly).
- Para CLIENT, se muestran las columnas: Nombre, Precio, Prep, Disponible, **Agregar**.

### 5. Landing page default
- En `App.tsx`, cambiar el redirect de `/` de `/categorias` a `/productos` para todos los roles.
- Agregar link "Carrito" en el nav.

## Risks / Trade-offs

- **[Persistencia] localStorage**: Si el usuario borra localStorage o usa modo incógnito que no persiste, el carrito se pierde. Aceptable para esta etapa.
- **[Concurrencia] Múltiples pestañas**: Si el usuario abre dos pestañas, cada una tiene su propio carrito en memoria, pero comparten localStorage. No se sincronizan en tiempo real. Aceptable.
- **[UX] Cantidad mínima 1**: El usuario no puede poner cantidad 0. Debe usar el botón "Eliminar" para sacar un producto del carrito.
