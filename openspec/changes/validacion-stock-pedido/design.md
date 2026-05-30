## Context

Actualmente el flujo de creación de pedidos desde el frontend del cliente es:

1. Cliente va a `/carrito` → hace clic en "Realizar Pedido"
2. Frontend envía `POST /pedidos/` con los items del carrito
3. Backend crea el pedido en estado PENDIENTE y hace auto-advance a CONFIRMADO
4. Si el stock es insuficiente, la excepción 409 se traga silenciosamente (`except Exception: pass`)
5. El pedido queda en PENDIENTE y el frontend muestra "Pedido creado exitosamente" (confuso)

Además, en la grilla de productos (`ProductosCRUD.tsx`), el botón "Agregar al carrito" se muestra siempre para todos los productos, incluso aquellos sin stock o no disponibles.

## Goals / Non-Goals

**Goals:**
- Validar stock disponible antes de crear el pedido, dando feedback al cliente
- Permitir al cliente ajustar cantidades o remover productos desde un modal cuando falte stock
- Deshabilitar el botón "Agregar al carrito" para productos sin stock o no disponibles
- Propagar correctamente errores de stock desde el backend al frontend

**Non-Goals:**
- No se modifica la lógica de deducción de stock (ya funciona en CONFIRMADO)
- No se implementa reposición de stock al cancelar (queda para otro cambio)
- No se modifica la lógica de visualización del pedido en PedidosPage (ya existe StockModal para admin/gestores)

## Decisions

### 1. Nuevo endpoint `POST /pedidos/validar-stock` vs validar en el create
- **Decisión**: Endpoint separado de solo lectura.
- **Por qué**: Permite al frontend verificar stock antes de enviar la orden, sin crear un pedido en PENDIENTE ni tener que lidiar con rollbacks. Es una operación idempotente y sin efectos secundarios.
- **Alternativa**: Modificar `POST /pedidos/` para que devuelva 409 antes de crear. Se descartó porque dejaría el pedido a medio crear en caso de error.

### 2. Fix del auto-advance silencioso
- **Decisión**: El auto-advance en `POST /pedidos/` DEBE propagar el error 409 al frontend.
- **Por qué**: Con la pre-validación, el stock casi siempre será suficiente, pero si hay una condición de carrera (otro usuario compró el mismo producto entre la validación y la creación), el frontend necesita saberlo para mostrar el modal de resolución.
- **Alternativa**: Dejar el `except Exception: pass` y confiar solo en la pre-validación. Se descartó porque es frágil ante condiciones de carrera.

### 3. Modal de advertencia de stock (StockWarningModal)
- **Decisión**: Componente inline en Carrito.tsx (mismo patrón que los demás modals del proyecto).
- **Por qué**: Consistencia con el patrón existente (todos los modals son inline). No justifica un componente separado.
- **Diseño**: Modal centrado con fondo oscuro. Tabla mostrando producto, cantidad solicitada, stock disponible. Input para ajustar cantidad y botón "Quitar" por fila. Botón "Confirmar cambios" que actualiza el carrito local y reintenta la validación.

### 4. Deshabilitar botón "Agregar al carrito"
- **Decisión**: Para productos sin medidas: deshabilitar si `!disponible` o `stock_cantidad === 0`.
- **Decisión**: Para productos con medidas: deshabilitar si NINGUNA medida está disponible con stock > 0.
- **Visual**: Botón gris con cursor-not-allowed y texto "Sin stock" o "No disponible" según corresponda.
- **Textos**: "Sin stock" cuando `disponible=true` pero stock=0. "No disponible" cuando `disponible=false`.

### 5. Validación de stock por medida en el nuevo endpoint
- **Decisión**: El endpoint reutiliza la misma lógica de `PedidoService.avanzar_estado()` pero sin efectos secundarios y sin requerir un pedido ya creado.
- **Implementación**: Función `validar_stock_items()` que recibe los mismos items que `DetallePedidoInput` y verifica stock contra `Producto.stock_cantidad` o `ProductoMedida.stock` según corresponda.

## Risks / Trade-offs

- **Race condition**: Entre la pre-validación y la creación del pedido, otro usuario podría comprar el último stock. → Mitigación: el auto-advance sigue validando stock al confirmar, y ahora propaga el error al frontend para que muestre el modal.
- **Rendimiento**: Para carritos con muchos items, la validación tiene que iterar sobre cada detalle. → Es trivial, N detalle promedio < 20 items.
- **UX**: El modal de advertencia aparece después de hacer clic en "Realizar Pedido". Es un paso adicional pero necesario para dar feedback útil.
