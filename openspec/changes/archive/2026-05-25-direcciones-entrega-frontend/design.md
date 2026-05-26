## Context

El backend de Direcciones de Entrega está completamente implementado (6 endpoints REST). El frontend no tiene absolutamente nada — ni API client, ni página, ni integración con el carrito. Los usuarios autenticados no pueden gestionar sus direcciones ni seleccionar una al hacer un pedido.

## Goals / Non-Goals

**Goals:**
- API client (`api/direcciones.ts`) con tipos y métodos para los 6 endpoints
- Página de gestión de direcciones (`DireccionesPage.tsx`) con CRUD completo
- Integración con el navbar (link para usuarios autenticados)
- Selector de dirección en `Carrito.tsx` con preselección de principal + opción de crear nueva
- Display de alias antepuesto a la dirección (ej: "Casa — Av. Siempre Viva 123")

**Non-Goals:**
- No tocar el backend
- No modificar el modelo de datos
- No agregar geolocalización ni mapas
- No implementar validación de coordenadas

## Decisions

1. **DireccionesPage como CRUD independiente**: Se crea una página dedicada (no modales en el carrito) para la gestión completa de direcciones. El carrito solo tendrá un dropdown selector + opción rápida de crear.

2. **Modales para crear/editar, no formularios inline**: Se reutiliza el patrón de popup/modal que ya existe en el proyecto (ej: DetallesPopup en PedidosPage). Más limpio que rutas anidadas.

3. **Dropdown en Carrito con fetch al montar**: Se carga `GET /direcciones/` al montar el componente. Si hay direcciones, se muestra el dropdown con la principal preseleccionada. Si no hay, se oculta y se muestra un botón "Agregar dirección".

4. **Opción "Agregar nueva dirección" en el dropdown**: Al final del dropdown, un item que abre un modal rápido para crear dirección. Tras crear, se refresca la lista y se selecciona la nueva.

5. **Alias visible siempre**: En listas y dropdowns, el formato es `"{alias} — {linea1}"` si tiene alias, o solo `"{linea1}"` si no. El alias no es requerido.

6. **direccion_id en CreatePedidoInput**: Se agrega campo opcional al tipo frontend y se envía en el POST. Si no se selecciona ninguna, no se envía y el backend auto-selecciona la principal.

## Risks / Trade-offs

- [Carga async] El dropdown de direcciones en el carrito requiere un fetch adicional al montar. → Mitigación: se hace en paralelo con la carga de productos, no bloquea la UI.
- [Estado inconsistente] Si el usuario crea/edita/elimina direcciones en otra pestaña, el dropdown del carrito queda desactualizado. → Mitigación: se recarga al enfocar la ventana (ya existe patrón con event listener "focus").
- [UX] El modal para crear dirección desde el carrito puede sentirse intrusivo. → Mitigación: es un modal pequeño con solo campos esenciales (alias, linea1, ciudad).
