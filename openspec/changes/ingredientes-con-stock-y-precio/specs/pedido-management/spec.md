## MODIFIED Requirements

### Requirement: Decrement ingredient stock on CONFIRMADO transition

When a pedido transitions to CONFIRMADO, the system SHALL additionally decrement `Ingrediente.stock_actual` for each ingredient of each product in the order. The decrement amount is `ProductoIngrediente.cantidad * DetallePedido.cantidad`, summed per ingredient across all order items.
(Previously: stock was only tracked at product/medida level, not at ingredient level)

#### Scenario: Order confirmation decrements ingredient stock

- **WHEN** an order with 2 "Pizza Margherita" (each using 0.3kg "Harina") transitions to CONFIRMADO
- **THEN** `Harina.stock_actual` is decremented by 0.6 (rounded to int 1)
- **THEN** the order transitions successfully to CONFIRMADO

### Requirement: Validate ingredient stock before confirmation

Before transitioning to CONFIRMADO, the system SHALL verify that each required ingredient has sufficient `stock_actual`. If any ingredient's stock is insufficient for the full order, the transition SHALL fail.

#### Scenario: Insufficient ingredient stock returns 409

- **WHEN** an order requires 5 units of "Harina" but `Harina.stock_actual` is only 3
- **THEN** the system returns 409 Conflict
- **THEN** the response body includes `{ "error": "stock_insuficiente", "details": [ { "ingrediente": "Harina", "disponible": 3, "requerido": 5 } ] }`
- **THEN** the order remains in its current state (PENDIENTE)

#### Scenario: Multiple ingredients insufficient

- **WHEN** an order requires ingredients where both "Harina" (req: 5, stock: 2) and "Queso" (req: 3, stock: 1) have insufficient stock
- **THEN** the response includes details for BOTH ingredients
- **THEN** the order does NOT transition

### Requirement: Products with medidas do not affect ingredient stock

Products that use medidas (primordial categories) and have NO `ProductoIngrediente` associations SHALL NOT trigger ingredient stock decrement on order confirmation.
(Previously: no ingredient stock logic existed for any product type)

#### Scenario: Medida-only product skips ingredient stock

- **WHEN** an order contains a product with medidas but no ingredient associations
- **THEN** the order transitions to CONFIRMADO without any ingredient stock operation
- **THEN** existing medida stock logic continues to apply
