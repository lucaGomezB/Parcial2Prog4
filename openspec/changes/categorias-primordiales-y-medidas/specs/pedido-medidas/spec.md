## ADDED Requirements

### Requirement: Carrito soporta medidas
El carrito (localStorage) DEBE almacenar la medida seleccionada al agregar un producto con medidas.
Los productos sin medidas DEBEN seguir funcionando como hoy.

#### Scenario: Cliente agrega producto con medida al carrito
- **WHEN** un cliente agrega "Coca Cola" con medida "500ml" al carrito
- **THEN** CarritoItem contiene productoId, nombre, precio (de la medida), cantidad, medidaId, medidaNombre
- **THEN** si el cliente vuelve a agregar el mismo producto con distinta medida, se crea un item separado

#### Scenario: Cliente agrega producto sin medida al carrito
- **WHEN** un cliente agrega un producto sin medidas al carrito
- **THEN** CarritoItem NO incluye medidaId ni medidaNombre (backward compatible)

#### Scenario: Selector de medida antes de agregar al carrito
- **WHEN** un cliente hace clic en "Agregar al carrito" en un producto con medidas
- **THEN** se muestra un selector/modal con las medidas disponibles (nombre + precio)
- **THEN** el cliente selecciona una medida y confirma la cantidad
- **THEN** el producto se agrega al carrito con la medida seleccionada

### Requirement: DetallePedido registra medida snapshot
El modelo DetallePedido DEBE tener un campo `medida_snapshot: Optional[str]` que congele el nombre de la medida al momento del pedido.

#### Scenario: Pedido con medidas registra snapshot
- **WHEN** un cliente crea un pedido con un producto que tiene medida
- **THEN** DetallePedido.medida_snapshot contiene el nombre de la medida (ej: "500ml")
- **THEN** precio_snapshot contiene el precio de la medida en ese momento
- **THEN** nombre_snapshot contiene el nombre del producto

#### Scenario: Pedido sin medidas no incluye snapshot
- **WHEN** un cliente crea un pedido con un producto sin medidas
- **THEN** DetallePedido.medida_snapshot es NULL
- **THEN** precio_snapshot contiene el precio_base del producto

### Requirement: Stock se descuenta por medida al confirmar pedido
Cuando un pedido avanza al estado CONFIRMADO, el sistema DEBE descontar stock de la medida específica. Si el producto no tiene medidas, descuenta de producto.stock_cantidad como hoy.

#### Scenario: Descuento de stock por medida
- **WHEN** un pedido con "Coca Cola 500ml" avanza a CONFIRMADO
- **THEN** se descuenta 1 del stock de la medida "500ml"
- **THEN** NO se descuenta de producto.stock_cantidad

#### Scenario: Descuento de stock sin medidas (backward compatible)
- **WHEN** un pedido con un producto sin medidas avanza a CONFIRMADO
- **THEN** se descuenta de producto.stock_cantidad como siempre

### Requirement: Frontend muestra medida en detalle del pedido
El detalle del pedido DEBE mostrar la medida seleccionada si existe.

#### Scenario: Ver medida en pedido
- **WHEN** un ADMIN o CLIENTE ve un pedido con productos que tienen medida
- **THEN** la tabla de detalles muestra columna "Medida" o el nombre de la medida junto al producto
- **THEN** si el producto no tiene medida, no se muestra nada extra
