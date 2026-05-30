## Context

El sistema actual trata a los ingredientes como entidades puramente cualitativas: solo tienen nombre, descripcion y flag de alergeno. El precio y stock se gestionan **exclusivamente a nivel de producto** (precio_base + stock_cantidad) o de medida (ProductoMedida.precio + ProductoMedida.stock).

No existe relacion entre el costo de los ingredientes y el precio del producto. Para un negocio de alimentos, esto es una deuda tecnica fundamental: el costo real del producto ES la suma de sus ingredientes, y el stock disponible depende de los insumos disponibles.

Este diseno agrega precio y stock a los ingredientes, y establece el precio base del producto como el calculo automatico de `SUM(ingrediente.precio_actual * cantidad_usada)`.

## Goals / Non-Goals

**Goals:**
- Agregar `precio_actual: Decimal` y `stock_actual: int` al modelo Ingrediente
- Agregar `cantidad: Decimal` a la tabla puente ProductoIngrediente
- Calcular automaticamente `precio_base` del producto como suma de ingredientes cuando tiene ingredientes
- Descontar stock de ingredientes al confirmar un pedido (CONFIRMADO)
- Actualizar CRUD de ingredientes en frontend para gestionar precio/stock
- Actualizar CRUD de productos en frontend para mostrar precio calculado y gestionar cantidad por ingrediente
- Actualizar seed data con precios y stocks iniciales

**Non-Goals:**
- Gestión de ordenes de compra / reposicion de ingredientes (proveedores)
- Alertas de stock minimo de ingredientes
- Versionado de recetas / historial de cambios en composicion de productos
- Integracion con sistema de lotes o vencimientos
- Modificacion del sistema de Medidas/ProductoMedida (productos con medidas siguen su logica actual)

## Decisions

### D1: Calculo de precio_base — almacenado, no bajo demanda
**Decision**: Almacenar `precio_base` calculado en la tabla `producto`, actualizandolo en cada operacion que afecte ingredientes.

**Alternativa considerada**: Calcular bajo demanda en cada GET.
- **Razon de rechazo**: Impacto en performance de listados (N+1 por cada producto en la tabla)
- **Trade-off**: Datos pueden quedar stale si cambia precio de ingrediente sin recalcular

**Trigger de recalculo**: En ProductoService, despues de:
- Agregar/quitar ingrediente a un producto
- Actualizar `cantidad` de un ProductoIngrediente
- Actualizar `precio_actual` de un Ingrediente (via nuevo endpoint o en update existente)

**Formula**: `precio_base = SUM(Ingrediente.precio_actual * ProductoIngrediente.cantidad for each ingrediente in producto.ingredientes)`

### D2: Precio manual vs calculado
**Decision**: Cuando un producto TIENE ingredientes, `precio_base` se recalcula automaticamente y el campo `precio_base` en el formulario de edicion se muestra como **read-only** con indicador "(calculado desde ingredientes)". Cuando NO tiene ingredientes, `precio_base` sigue siendo manual como hoy.

**Alternativa considerada**: Permitir override manual con flag "usar precio manual".
- **Razon de rechazo**: Complejidad adicional innecesaria. Si el usuario quiere un precio distinto, puede quitar ingredientes o ajustar cantidades.
- **Excepcion**: Productos con medidas (categoria primordial) no se ven afectados — siguen usando `precio` por medida.

### D3: Descuento de stock de ingredientes al confirmar pedido
**Decision**: En `PedidoService.avanzar_estado()` al transicionar a CONFIRMADO, ademas del descuento actual (producto.stock_cantidad o ProductoMedida.stock), se agrega descuento de `Ingrediente.stock_actual`:

```python
for detalle in pedido.detalles:
    for pi in detalle.producto.ingredientes:
        ingrediente = pi.ingrediente
        cantidad_a_descontar = pi.cantidad * detalle.cantidad
        if ingrediente.stock_actual < cantidad_a_descontar:
            raise HTTPException(409, f"Stock insuficiente de {ingrediente.nombre}")
        ingrediente.stock_actual -= cantidad_a_descontar
```

**Alternativa considerada**: Descontar SOLO ingredientes (no producto/medida).
- **Razon de rechazo**: Ambos conceptos de stock coexisten. El stock de producto representa unidades fisicas terminadas; el stock de ingrediente representa materia prima. Ambos deben decrementarse.

### D4: Migracion sin Alembic
**Decision**: Agregar las columnas directamente via `SQLModel.metadata.create_all()` como el resto del proyecto. Alembic se implementara en un change separado (`alembic-migrations`) y en ese momento capturara el schema actualizado.

**Alternativa considerada**: Bloquear este change hasta tener Alembic.
- **Razon de rechazo**: El proyecto completo usa `create_all()` actualmente. Bloquear un cambio arquitectonico fundamental por una herramienta de migracion es poner el carro delante del caballo.

### D5: Nuevo endpoint para actualizar precio/stock de ingrediente
**Decision**: Agregar endpoints dedicados en el router de Ingrediente:
- `PATCH /ingredientes/{id}/precio` — actualiza solo `precio_actual` y dispara recalculo de precio_base en todos los productos que usan ese ingrediente
- `PATCH /ingredientes/{id}/stock` — actualiza solo `stock_actual` (ajuste manual de inventario)

El update generico `PATCH /ingredientes/{id}` sigue existiendo pero NO incluye `precio_actual` ni `stock_actual` — esos campos tienen endpoints dedicados por claridad y para separar concerns (datos de catalogo vs datos de inventario).

**Alternativa considerada**: Incluir precio/stock en el PATCH generico.
- **Razon de rechazo**: Mezclar datos de catalogo (nombre, descripcion, alergeno) con datos de inventario (precio, stock) en el mismo endpoint. Los endpoints dedicados permiten mejor auditoria y logica de recalculo.

### D6: ProductoIngrediente.cantidad como Decimal
**Decision**: El campo `cantidad` en `ProductoIngrediente` es `Decimal(10,2)` para permitir fracciones (ej: 0.5 kg de harina, 1.5 tazas de azucar).

**Alternativa considerada**: Entero.
- **Razon de rechazo**: Muchas recetas usan fracciones de ingredientes (medio kilo, 1/4 taza, etc.).

## Risks / Trade-offs

- **Staleness de precio_base**: Si se cambia `precio_actual` de un ingrediente via otro canal (DB directa, otro servicio), el `precio_base` de productos no se recalcula. **Mitigacion**: Todos los cambios pasan por los endpoints dedicados que disparan recalculo.
- **Performance en confirmacion de pedido**: Si un pedido tiene muchos productos con muchos ingredientes, el descuento iterativo puede ser lento. **Mitigacion**: Los ingredientes por producto suelen ser < 20 items. No se anticipa problema.
- **Rollback de confirmacion**: Si el descuento de stock de ingredientes falla a mitad del loop, algunos ingredientes quedan descontados y otros no. **Mitigacion**: Todo ocurre dentro de una misma transaccion (UoW). Si falla, TODO se revierte.
- **Productos con medidas + ingredientes**: Actualmente los productos en categorias primordiales NO requieren ingredientes. Si en el futuro se les agregan, el precio calculado entraria en conflicto con el precio por medida. **Mitigacion**: Este cambio NO modifica la logica de medidas. Si un producto tiene medidas, su precio_base no se recalcula desde ingredientes.
