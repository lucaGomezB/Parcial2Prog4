## REMOVED Requirements

### Requirement: medida_id in DetallePedidoInput
**Reason**: Simplified to always use Producto.stock_cantidad
**Migration**: DetallePedidoInput no longer accepts medida_id

### Requirement: medida_snapshot in DetallePedido
**Reason**: No longer needed — no bifurcated stock logic
**Migration**: Existing historical records retain medida_snapshot value. New records have NULL.

### Requirement: Bifurcated stock deduction (product vs medida)
**Reason**: Removed in favor of single-stock model
**Migration**: PedidoService always deducts from Producto.stock_cantidad (or Ingrediente.stock_actual if ingredients present)
