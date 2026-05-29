## Context

Actualmente los productos tienen `precio_base`, `stock_cantidad` y `disponible` como campos directos. Las categorías tienen una estructura de árbol con `parent_id`. No existe concepto de variantes/tamaños/porciones.

Para modelar "Coca Cola 250ml/500ml/1L" como un solo producto con múltiples presentaciones, se necesita una entidad `ProductoMedida` y un flag en categoría que indique qué categorías habilitan este comportamiento.

## Goals / Non-Goals

**Goals:**
- Permitir que un producto tenga N medidas con precio y stock propio
- Marcar categorías como "primordiales" para indicar que sus productos usan medidas
- Cliente selecciona medida al agregar al carrito
- Stock se descuenta por medida, no por producto
- Editor de stock adaptado para stock por medida
- Seed con datos de ejemplo
- Backward compatible: productos sin medidas siguen funcionando exactamente como hoy

**Non-Goals:**
- No se modifican precios en medidas existentes (no hay historial de precios por medida)
- No hay combinaciones de medidas (ej: no se puede elegir "2 medidas distintas" en un mismo ítem)
- No hay herencia de medidas entre categorías (cada producto define sus propias medidas)
- No se afecta el flujo de pedidos existentes (los snapshots ya están en DetallePedido)

## Decisions

### 1. Modelo: ProductoMedida como tabla independiente

```
ProductoMedida
├── id: int (PK)
├── producto_id: int (FK → Producto.id, NOT NULL)
├── nombre: str (ej: "250ml", "500ml", "1L", "1 porción", "entera")
├── precio: Decimal(10,2)  ← precio PROPIO de esta medida
├── stock: int              ← stock PROPIO de esta medida
├── orden: int              ← orden de visualización
└── created_at, updated_at (TimestampModel)
```

**Alternativa descartada:** Store medidas como JSON en el producto. No permite queries eficientes, no tiene FK constraints, difícil de mantener.

### 2. Precio por medida, no multiplicador

Cada `ProductoMedida` tiene su propio `precio`. No se usa `precio_base * factor`.

**Por qué:** Un multiplcador (ej: 1.5x, 2.0x) forza relaciones de precio que no siempre se cumplen en la realidad (ej: 1L de Coca no cuesta 4x lo que cuesta 250ml). Precio explícito es más flexible y predecible.

### 3. Regla de negocio: si tiene medidas → ignora precio_base y stock_cantidad

```
SI producto.medidas.count > 0:
  - precio_efectivo = precio de la medida elegida
  - stock_efectivo = stock de la medida elegida
  - disponible = any(medida.stock > 0 for medida in producto.medidas)
  - producto.precio_base y producto.stock_cantidad NO se usan

SI producto.medidas.count == 0:
  - Funciona exactamente como hoy (backward compatible)
```

### 4. Categoria.es_primordial como trigger visual

El flag `es_primordial` en Categoria **no** fuerza nada a nivel backend — es un hint para el frontend de que debe mostrar la sección "Medidas" en el formulario. El backend permite medidas en cualquier producto.

**Alternativa descartada:** Validar en backend que un producto con medidas SOLO pueda estar en categorías primordiales. Agrega complejidad innecesaria y rompe si alguien re-categoriza un producto después.

### 5. Stock: descuento por medida al confirmar pedido

Cuando un pedido avanza a CONFIRMADO, se descuenta `stock` de la `ProductoMedida` específica (no del `Producto.stock_cantidad`).

Si el producto no tiene medidas → descuenta `Producto.stock_cantidad` como hoy.

### 6. Snapshot en DetallePedido

Se agrega `medida_snapshot: Optional[str]` a `DetallePedido`. Esto congela el nombre de la medida al momento del pedido (ej: "500ml"), siguiendo el mismo patrón snapshot de `nombre_snapshot` y `precio_snapshot`.

### 7. Carrito (localStorage)

```typescript
interface CarritoItem {
  productoId: number;
  nombre: string;
  precio: number;       // precio de la medida seleccionada
  cantidad: number;
  medidaId?: number;     // ID de la medida (opcional, solo si aplica)
  medidaNombre?: string; // snapshot "500ml"
}
```

### 8. API — Endpoints de Medidas

```
GET    /productos/{producto_id}/medidas/        → listar medidas
POST   /productos/{producto_id}/medidas/        → crear medida
PATCH  /productos/{producto_id}/medidas/{id}    → actualizar medida (precio, stock, nombre, orden)
DELETE /productos/{producto_id}/medidas/{id}    → eliminar medida
```

Anidados bajo producto porque no tienen sentido independiente. Reutilizan `require_roles(["ADMIN"])`.

### 9. Frontend — Modificaciones

```
ProductosCRUD.tsx:
  - Al crear/editar, si existe al menos una categoría primordial seleccionada
    → muestra sección "Medidas" en el formulario (inline, arriba de botones)
  - Cada medida: nombre, precio, stock, botón quitar, botón agregar

Stock Editor:
  - Si producto.medidas.length > 0 → tabla inline con stock por medida
  - Si no → input de stock_cantidad como hoy

Carrito.tsx + carrito.ts:
  - Al agregar producto con medidas → modal/selector de medida antes de agregar
  - CarritoItem incluye medidaId y medidaNombre
  - Al crear pedido → envía medidaId en DetallePedidoInput

PedidosPage.tsx:
  - Muestra medida_snapshot si existe en el detalle
```

## Risks / Trade-offs

- **[Rendimiento]** Productos con muchas medidas (10+) pueden hacer el formulario pesado → mitigado con paginación virtual si es necesario
- **[Consistencia]** Si se elimina una medida que está en carritos sin finalizar → el carrito queda con un medidaId huérfano. El POST /pedidos/ debe validar que la medida existe antes de crear el detalle
- **[Seed]** El seed actual es idempotente pero los nuevos datos de medidas deben serlo también
- **[Stock]** El descuento de stock en medidas debe ser atómico con la transacción del pedido para evitar over-selling
