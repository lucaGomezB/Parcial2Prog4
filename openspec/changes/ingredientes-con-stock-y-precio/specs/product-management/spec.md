## MODIFIED Requirements

### Requirement: Precio_base becomes auto-calculated when ingredients exist

Previously, `precio_base` was a fully manual field. Now, when a product has at least one `ProductoIngrediente` association, its `precio_base` SHALL be auto-calculated as `SUM(ingredient.precio_actual * pi.cantidad)` and the field SHALL be read-only in the form. Products with medidas (primordial categories) or without ingredients SHALL keep the existing manual behavior.
(Previously: `precio_base` was always manually editable regardless of ingredients)

#### Scenario: Product with ingredients shows calculated price

- **WHEN** an admin views a product that has 3 ingredients defined
- **THEN** the product form shows `precio_base` as a read-only field displaying the calculated value
- **THEN** the form shows a label "Calculado desde ingredientes" next to the field

#### Scenario: Product without ingredients keeps editable precio_base

- **WHEN** an admin views a product with zero ingredient associations
- **THEN** `precio_base` is editable as before
- **THEN** there is no auto-calculation applied

#### Scenario: Product with medidas keeps manual precio_base

- **WHEN** a product belongs to a primordial category and has medidas defined
- **THEN** `precio_base` remains manually editable
- **THEN** ingredient cost calculation does NOT affect `precio_base`

### Requirement: Product form shows ingredient cantidad per row

When editing a product's ingredients, each `ProductoIngrediente` row in the product form SHALL display and allow editing of the `cantidad` field alongside the ingredient selector.

#### Scenario: Admin adjusts ingredient cantidad

- **WHEN** an admin edits the ingredient list of a product and changes the `cantidad` of "Harina" from 0.5 to 1.0
- **THEN** the UI updates the `cantidad` value via PATCH `/productos/{id}/ingredientes/{ingrediente_id}`
- **THEN** the product's `precio_base` auto-updates to reflect the change in real time

### Requirement: Product list displays calculated price

The product list view (table/list) SHALL show the `precio_base` field. For products with auto-calculated prices, the value displayed SHALL be the calculated total.
(Previously: all products showed the manually-entered `precio_base`)

#### Scenario: List shows calculated values

- **WHEN** an admin views the product list
- **THEN** the `precio_base` column shows the calculated price for products with ingredients
- **THEN** the column shows the manual price for products without ingredients
