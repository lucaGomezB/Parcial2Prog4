## ADDED Requirements

### Requirement: Pre-validación de stock
El sistema DEBE permitir verificar la disponibilidad de stock para un conjunto de items (producto + cantidad + medida opcional) ANTES de crear un pedido, sin generar efectos secundarios.

#### Scenario: Stock suficiente para todos los items
- **WHEN** el frontend envía una solicitud de validación de stock con items cuyas cantidades no superan el stock disponible
- **THEN** el sistema responde con `{ valido: true }` y código 200

#### Scenario: Stock insuficiente en uno o más items
- **WHEN** el frontend envía una solicitud de validación con items donde al menos uno supera el stock disponible
- **THEN** el sistema responde con `{ valido: false, detalles: [ ... ] }` y código 200, listando cada producto con problema, su stock disponible y cantidad solicitada

#### Scenario: Item sin medida especificada verifica stock_cantidad del producto
- **WHEN** el item de validación no incluye `medida_id`
- **THEN** el sistema verifica contra `Producto.stock_cantidad`

#### Scenario: Item con medida especificada verifica stock de la medida
- **WHEN** el item de validación incluye `medida_id`
- **THEN** el sistema verifica contra `ProductoMedida.stock` correspondiente

#### Scenario: Medida no encontrada para el producto
- **WHEN** el `medida_id` especificado no existe o no pertenece al producto indicado
- **THEN** el sistema responde con error 400 indicando que la medida no fue encontrada

### Requirement: Productos sin stock no agregables al carrito
El sistema DEBE mostrar los productos sin stock o no disponibles en la grilla de productos, pero NO DEBE permitir agregarlos al carrito.

#### Scenario: Producto simple sin stock muestra botón deshabilitado
- **WHEN** un producto sin medidas tiene `stock_cantidad === 0` y `disponible === true`
- **THEN** se muestra en la grilla con el botón "Agregar al carrito" deshabilitado y texto "Sin stock"

#### Scenario: Producto no disponible muestra botón deshabilitado
- **WHEN** un producto tiene `disponible === false`
- **THEN** se muestra en la grilla con el botón "Agregar al carrito" deshabilitado y texto "No disponible"

#### Scenario: Producto con medidas sin stock muestra botón deshabilitado
- **WHEN** un producto con medidas tiene TODAS sus medidas con stock = 0 o `disponible = false`
- **THEN** se muestra en la grilla con el botón "Agregar al carrito" deshabilitado y texto "Sin stock"

#### Scenario: Producto con al menos una medida disponible muestra botón habilitado
- **WHEN** un producto con medidas tiene AL MENOS una medida con stock > 0 y `disponible = true`
- **THEN** se muestra en la grilla con el botón "Agregar al carrito" habilitado

### Requirement: Modal de advertencia de stock en el checkout
El sistema DEBE mostrar un modal de advertencia cuando el stock sea insuficiente al intentar realizar un pedido, permitiendo al usuario ajustar cantidades o remover productos.

#### Scenario: Stock insuficiente muestra modal con opciones
- **WHEN** el usuario hace clic en "Realizar Pedido" y la validación de stock detecta insuficiencias
- **THEN** se muestra un modal que lista cada producto problema con: nombre, cantidad solicitada, stock disponible, input para nueva cantidad, y botón para quitar el producto

#### Scenario: Usuario reduce cantidad en el modal
- **WHEN** el usuario reduce la cantidad de un producto en el modal a un valor ≤ stock disponible
- **THEN** al hacer clic en "Confirmar Cambios", el carrito se actualiza con las nuevas cantidades y se reintenta la validación/creación

#### Scenario: Usuario remueve producto del modal
- **WHEN** el usuario hace clic en "Quitar" para un producto en el modal
- **THEN** el producto se elimina del carrito local y se reintenta la validación/creación

#### Scenario: Stock insuficiente en auto-advance (race condition)
- **WHEN** el stock se agota entre la pre-validación y la creación del pedido (auto-advance falla con 409)
- **THEN** el frontend captura el error 409 con `stock_insuficiente` y muestra el mismo modal de advertencia
