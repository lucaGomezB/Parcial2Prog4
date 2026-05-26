## Context

Actualmente los campos monetarios en Pedido, DetallePedido y Pago usan tipo `float` de Python. `float` tiene precisión de punto flotante IEEE 754 (~15-17 dígitos significativos) que puede causar errores de redondeo en operaciones aritméticas. El ERD v5 especifica DECIMAL(10,2) — 10 dígitos totales, 2 decimales. `Producto.precio_base` ya lo implementa correctamente.

## Goals / Non-Goals

**Goals:**
- Migrar todos los campos `float` monetarios a `Decimal` con `Numeric(precision=10, scale=2)` en modelos SQLModel
- Actualizar schemas Pydantic para reflejar el tipo `Decimal`
- Mantener compatibilidad total con la API existente (Decimal se serializa como float en JSON)

**Non-Goals:**
- No cambiar lógica de negocio ni cálculos existentes
- No tocar campos no monetarios que usen `float` (latitud, longitud)
- No modificar Producto.precio_base (ya es Decimal correctamente)

## Decisions

### Pattern for Decimal fields
Usar el mismo patrón que `Producto.precio_base`:
```python
from decimal import Decimal
from sqlmodel import Field, Column
from sqlalchemy import Numeric

precio_base: Decimal = Field(
    default=Decimal('0.00'),
    sa_column=Column(Numeric(precision=10, scale=2))
)
```

### VARCHAR vs CHAR para hashes
El ERD especifica `CHAR(60)` para `password_hash` y `CHAR(64)` para `token_hash`. El código actual usa `max_length=60` / `max_length=64` que genera columnas `VARCHAR`. Se decide **mantener VARCHAR** porque:
- PostgreSQL trata CHAR y VARCHAR como casi idénticos (diferencia solo en padding con espacios)
- bcrypt y SHA-256 siempre producen strings de longitud fija exacta, no hay riesgo de almacenar datos inválidos
- VARCHAR es el estándar del código base y evita migraciones innecesarias

### SoftDeleteModel en Ingrediente
El ERD v5 no lista `deleted_at` para Ingrediente, pero el código lo incluye vía `SoftDeleteModel`. Se **mantiene** porque:
- Es una medida defensiva (permite "desactivar" ingredientes sin perder datos históricos)
- El repository ya filtra `deleted_at IS NULL`, así que es transparente
- No hay impacto negativo en rendimiento

### Campos extra fuera del ERD
Los campos `tiempo_prep_min` (Producto), `orden_display` (Categoria), y `es_principal`/`orden` (ProductoIngrediente) no están en el ERD v5 pero se **mantienen** porque:
- Son funcionales y potencialmente útiles para features futuras
- No interfieren con el modelo de datos ni con las relaciones existentes
- Eliminarlos requeriría migraciones sin beneficio claro

### Schema compatibility
Pydantic v2 maneja `Decimal` de forma nativa y lo serializa a JSON como `float`. No hay breaking changes en la API — los endpoints siguen devolviendo los mismos valores numéricos.

## Risks / Trade-offs

- **[Risk] Cálculos existentes**: Algunos servicios hacen operaciones aritméticas (subtotal - descuento + costo_envio = total). Con `float`, estas operaciones podían tener errores de redondeo. Con `Decimal`, serán precisas pero ligeramente más lentas. → Mitigation: El rendimiento no es crítico para estas operaciones.
- **[Trade-off] Decimal es más verboso**: Requiere importar `Decimal` y `Numeric` en cada archivo, y usar `Decimal('0.00')` en vez de `0.0`.
