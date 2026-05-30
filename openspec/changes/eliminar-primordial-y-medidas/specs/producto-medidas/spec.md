## REMOVED Requirements

### Requirement: ProductoMedida model
**Reason**: Replaced by product-level pricing + ingredient-based cost calculation
**Migration**: Products that previously used medidas now use precio_base and stock_cantidad directly. If the product has ingredients, precio_base is auto-calculated from ingredient costs.

### Requirement: Medidas CRUD endpoints
**Reason**: Removed with ProductoMedida model
**Migration**: No replacement needed

### Requirement: Medidas in Producto schemas
**Reason**: ProductoMedida model removed
**Migration**: ProductoCreate and ProductoRead no longer include medidas field

### Requirement: Primordial category flag
**Reason**: Concept of "primordial categories" was a design error — no real-world equivalent
**Migration**: Categoria no longer has es_primordial field. All products require ingredients.
