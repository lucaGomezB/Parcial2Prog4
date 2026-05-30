## Context

El sistema actual tiene dos conceptos que se eliminan:

1. **Categoria primordial** (`es_primordial`): Un flag en Categoria que indica que los productos de esa categoria pueden tener medidas. Esto no tiene sentido en un dominio de alimentos — ninguna categoria "habilita" un tipo de pricing.

2. **ProductoMedida** (medidas/porciones): Variantes de un producto con precio y stock propio. Esto duplica la logica de pricing (que ahora se calcula desde ingredientes) y complejifica innecesariamente el sistema.

Con la implementacion de `ingredientes-con-stock-y-precio`, el precio base del producto se calcula automaticamente desde sus ingredientes. Tener medidas como sistema paralelo de pricing es inconsistente.

## Goals / Non-Goals

**Goals:**
- Eliminar el campo `es_primordial` de Categoria (modelo, schemas, frontend)
- Eliminar la tabla `ProductoMedida` (modelo, schemas, service methods, router endpoints)
- Eliminar `medida_snapshot` y `medida_id` del sistema de Pedidos
- Simplificar ProductoService: eliminar toda logica de medidas
- Simplificar PedidoService: stock siempre se descuenta de `Producto.stock_cantidad`
- Simplificar frontend: eliminar MedidaSelectorModal, eliminar logica de medidas en ProductosCRUD, Carrito, carrito.ts
- Actualizar seed data

**Non-Goals:**
- No se modifican los productos existentes (solo se elimina la capacidad de tener medidas)
- No se afecta la logica de `ingredientes-con-stock-y-precio` — al reves, la refuerza
- No se migran datos historicos (medida_snapshot en pedidos existentes se pierde)

## Decisions

### D1: Orden de eliminacion — Backend primero, Frontend despues
**Decision**: Eliminar primero todo el backend (modelos, schemas, services, routers), luego el frontend.

**Razon**: El backend es la base. Una vez que el backend no expone medidas, el frontend no puede consumirlas. Esto evita estados inconsistentes.

### D2: La columna `medida_snapshot` se deja NULLable, no se dropea
**Decision**: No eliminar la columna `medida_snapshot` de la tabla `detallepedido` para no perder datos historicos. Simplemente se deja de escribir y leer.

**Alternativa considerada**: Dropear la columna.
- **Razon de rechazo**: Datos historicos en pedidos existentes. Mejor mantener la columna como NULL para registros nuevos y dejar los viejos intactos.

### D3: Productos con medidas actuales se convierten en productos simples
**Decision**: Los productos que actualmente tienen `ProductoMedida` registros pierden el acceso a esas medidas. El `precio_base` y `stock_cantidad` del producto (que ya existen) pasan a ser los valores efectivos.

**Razon**: Los campos `precio_base` y `stock_cantidad` ya existen en `Producto` y siempre tuvieron valores (default 0). Al eliminar medidas, el producto funciona como modo simple. Si el producto tiene ingredientes, su `precio_base` se recalcula desde ellos (por el cambio `ingredientes-con-stock-y-precio`).

### D4: La tabla `productomedida` se dropea via create_all()
**Decision**: Al eliminar la clase `ProductoMedida` del modelo, `SQLModel.metadata.create_all()` ya no crea la tabla. Si la tabla existe en la BD, simplemente se ignora (no se dropea automaticamente).

**Alternativa considerada**: Agregar DROP TABLE explicito.
- **Razon de rechazo**: `create_all()` es CREATE IF NOT EXISTS — no dropea. Dejar la tabla huerfana es seguro y permite rollback. Si se quiere limpiar, se hace manualmente.

### D5: Todos los productos requieren ingredientes ahora
**Decision**: Al eliminar `es_primordial`, se elimina el escape hatch que permitia productos sin ingredientes. TODO producto debe tener al menos 1 ingrediente.

**Excepcion**: Productos con medidas existentes (que al migrar pierden las medidas) deberan tener ingredientes asignados para funcionar correctamente.

## Migration Plan

1. Eliminar backend models + schemas (ProductoMedida, es_primordial, medida_snapshot)
2. Eliminar backend service methods (medidas CRUD, primordial validation)
3. Eliminar backend router endpoints (medidas CRUD)
4. Eliminar frontend types (ProductoMedida, medida fields)
5. Eliminar frontend components (MedidaSelectorModal, medidas sections)
6. Eliminar frontend carrito logic (medidaId, medidaNombre)
7. Actualizar seed data
8. Archivar el viejo change `categorias-primordiales-y-medidas`
9. Verificar que todo compila y funciona
