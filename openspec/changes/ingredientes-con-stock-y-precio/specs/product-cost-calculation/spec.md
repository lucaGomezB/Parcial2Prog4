## ADDED Requirements

### Requirement: ProductoIngrediente has cantidad field

The `ProductoIngrediente` join model MUST have `cantidad: Decimal(10,2)` indicating how much of the ingredient the product uses. Each product-ingredient association SHALL carry its own cantidad.

#### Scenario: Creating product with ingredient cantidad

- **WHEN** a POST `/productos/{id}/ingredientes/` is called with `{ "ingrediente_id": 1, "cantidad": 0.5 }`
- **THEN** the association is created with `cantidad: 0.5`
- **THEN** the product's `precio_base` is recalculated

#### Scenario: Updating ingredient cantidad triggers recalculation

- **WHEN** a PATCH `/productos/{id}/ingredientes/{ingrediente_id}` is called with `{ "cantidad": 1.0 }`
- **THEN** the association's `cantidad` is updated to 1.0
- **THEN** the product's `precio_base` is recalculated

### Requirement: Precio_base auto-calculated from ingredients

When a product has at least one `ProductoIngrediente` association, its `precio_base` MUST be auto-calculated as `SUM(ingrediente.precio_actual * ProductoIngrediente.cantidad)` across all its ingredients.

#### Scenario: Product with 3 ingredients calculates correct total

- **WHEN** a product uses Ingredient A (precio_actual=100, cantidad=2), Ingredient B (precio_actual=50, cantidad=1), and Ingredient C (precio_actual=200, cantidad=0.5)
- **THEN** `precio_base` is calculated as (100 * 2) + (50 * 1) + (200 * 0.5) = 350
- **THEN** GET `/productos/{id}` returns `precio_base: 350`

#### Scenario: Adding ingredient to product recalculates price

- **WHEN** a product currently has `precio_base: 200` based on 2 ingredients
- **THEN** a new ingredient with precio_actual=50, cantidad=2 is added
- **THEN** `precio_base` is recalculated to 200 + (50 * 2) = 300

#### Scenario: Changing ingredient price recalculates all affected products

- **WHEN** Ingredient "Harina" has `precio_actual: 100` and is used by 3 different products
- **THEN** a PATCH to update Harina's precio_actual to 120 via the ingredient-inventory endpoint
- **THEN** all 3 products have their `precio_base` recalculated

### Requirement: Products with medidas do NOT auto-calculate

Products belonging to categories marked as `es_primordial` (which use medidas/measures) MUST NOT auto-calculate `precio_base` from ingredients. Each medida has its own price, and the product's ingredient-level cost is not shown as the base price.

#### Scenario: Product with medidas does NOT auto-calculate

- **WHEN** a product belongs to a primordial category and has medidas defined
- **THEN** adding or removing ingredients does NOT change the product's `precio_base`
- **THEN** `precio_base` remains the manual value set by the admin

### Requirement: Products without ingredients keep manual precio_base

Products that have NO `ProductoIngrediente` associations MUST keep their existing manual `precio_base` behavior unchanged.

#### Scenario: Product without ingredients maintains manual price

- **WHEN** a product has zero ingredients and an admin sets `precio_base: 500`
- **THEN** `precio_base` stays at 500 regardless of any ingredient price changes
- **THEN** the admin can freely edit `precio_base` via the product form

### Requirement: Recalculation triggers

The system SHALL trigger `precio_base` recalculation in these operations:
- An ingredient is added to or removed from a product
- The `cantidad` of a ProductoIngrediente is modified
- An ingredient's `precio_actual` is updated (via PATCH `/ingredientes/{id}/precio`)

#### Scenario: Removing ingredient recalculates price

- **WHEN** an ingredient is removed from a product that has 3 ingredients
- **THEN** `precio_base` is reduced by the removed ingredient's contribution
- **THEN** the new total reflects only the remaining 2 ingredients
