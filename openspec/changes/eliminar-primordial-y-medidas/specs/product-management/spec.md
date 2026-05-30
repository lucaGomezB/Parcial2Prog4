## MODIFIED Requirements

### Requirement: Product price is at product level (was: can be at medida level)
**FROM**: Products in primordial categories can have multiple medidas, each with its own price and stock. precio_base and stock_cantidad are used only when no medidas exist.
**TO**: Products ALWAYS use precio_base and stock_cantidad at the product level. No more medidas.

### Requirement: Product availability calculation
**FROM**: If product has medidas, disponible = any medida has stock > 0. If no medidas, disponible = stock_cantidad > 0.
**TO**: disponible = stock_cantidad > 0 (or ingredient-based if the ingredient-inventory system is active)
