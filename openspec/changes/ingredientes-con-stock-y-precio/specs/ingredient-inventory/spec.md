## ADDED Requirements

### Requirement: Ingredient has price and stock fields

The `Ingrediente` model MUST have `precio_actual: Decimal(10,2)` (default 0) and `stock_actual: int` (default 0) fields.

#### Scenario: Creating ingredient with price and stock

- **WHEN** a POST `/ingredientes/` request includes `precio_actual: 150.00` and `stock_actual: 100`
- **THEN** the ingredient is created with those values persisted
- **THEN** the response includes `precio_actual: 150.00` and `stock_actual: 100`

#### Scenario: Creating ingredient without price and stock

- **WHEN** a POST `/ingredientes/` request omits `precio_actual` and `stock_actual`
- **THEN** the ingredient is created with `precio_actual: 0` and `stock_actual: 0`

### Requirement: GET endpoints include price and stock

The `GET /ingredientes/` and `GET /ingredientes/{id}` endpoints MUST include `precio_actual` and `stock_actual` in the response body.

#### Scenario: List includes new fields

- **WHEN** a GET `/ingredientes/` request is made
- **THEN** every ingredient in the response includes `precio_actual` and `stock_actual` fields

#### Scenario: Detail includes new fields

- **WHEN** a GET `/ingredientes/{id}` request is made for an existing ingredient
- **THEN** the response includes `precio_actual` and `stock_actual` fields

### Requirement: Update ingredient price triggers recalculation

The system MUST expose `PATCH /ingredientes/{id}/precio` accepting `{ "precio_actual": Decimal }`. After updating the price, the system SHALL trigger recalculation of `precio_base` for ALL products that use this ingredient.

#### Scenario: Successful price update triggers recalculation

- **WHEN** a PATCH `/ingredientes/{id}/precio` is called with `{ "precio_actual": 200.00 }`
- **THEN** the ingredient's `precio_actual` is updated to 200.00
- **THEN** each product using this ingredient has its `precio_base` recalculated

#### Scenario: Price update with invalid value

- **WHEN** a PATCH `/ingredientes/{id}/precio` is called with `{ "precio_actual": -10 }`
- **THEN** the system returns 422 with validation error

### Requirement: Update ingredient stock

The system MUST expose `PATCH /ingredientes/{id}/stock` accepting `{ "stock_actual": int }` for manual inventory adjustments.

#### Scenario: Successful stock update

- **WHEN** a PATCH `/ingredientes/{id}/stock` is called with `{ "stock_actual": 50 }`
- **THEN** the ingredient's `stock_actual` is updated to 50
- **THEN** existing product prices are NOT affected

#### Scenario: Stock update with negative value

- **WHEN** a PATCH `/ingredientes/{id}/stock` is called with `{ "stock_actual": -5 }`
- **THEN** the system returns 422 with validation error

### Requirement: Decrement ingredient stock on order confirmation

When a pedido transitions to CONFIRMADO, the system SHALL decrement `stock_actual` of each ingredient used in the order's products, multiplied by the DetallePedido `cantidad` and the ProductoIngrediente `cantidad`.

#### Scenario: Insufficient ingredient stock prevents order confirmation

- **WHEN** an order contains a product requiring 2 units of "Harina" and `Harina.stock_actual` is 1
- **THEN** the system SHALL return 409 with details of which ingredients have insufficient stock
- **THEN** the order SHALL NOT transition to CONFIRMADO

#### Scenario: Sufficient stock decrements on confirmation

- **WHEN** an order has 3 products each using 0.5kg of "Harina" and `Harina.stock_actual` is 10
- **THEN** the order SHALL transition to CONFIRMADO
- **THEN** `Harina.stock_actual` SHALL be decremented by 1.5 (rounded to int)
