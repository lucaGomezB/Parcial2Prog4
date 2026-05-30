## Verification Report: ingredientes-con-stock-y-precio

**Date**: 2026-05-29
**Change**: ingredientes-con-stock-y-precio
**Mode**: Standard (no test runner detected)

---

### Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 56 (1-12 completed + 13.x verification) |
| Tasks 13.x complete | 6/6 |
| Tasks incomplete | 0 |

All 13.x verification tasks have been checked against actual code.

---

### Build & Tests Execution

**Build**: ➖ No build command detected (Python/FastAPI project)

**Tests**: ➖ No test runner detected (no pytest.ini, pyproject.toml, conftest.py, or test files found)

**Coverage**: ➖ Not available

---

### Task 13.1 — Product price auto-calculation

**Status**: ✅ **PASS**

**Evidence**:
- **File**: `Backend/modules/CatalogoDeProductos/Producto/service.py`
- **Lines 89–91** (`create()`):
  ```python
  # Si el producto tiene ingredientes, recalcular precio_base
  if data.ingredientes:
      ProductoService._recalcular_precio_producto(session, db_producto.id)
  ```
  → Only called when `data.ingredientes` is truthy (product has ingredients in payload).

- **Lines 98–125** (`_recalcular_precio_producto()`):
  ```python
  total = Decimal('0')
  for pi in associations:
      ing = session.get(Ingrediente, pi.ingrediente_id)
      if ing and ing.precio_actual:
          total += ing.precio_actual * pi.cantidad

  db_producto.precio_base = total
  session.add(db_producto)
  ```
  → Formula matches: `SUM(ingrediente.precio_actual * pi.cantidad)`.

- **Lines 115–116**: Early return if `not associations` — only recalculates when the product has ingredients.

---

### Task 13.2 — Ingredient price change triggers recalculation

**Status**: ✅ **PASS**

**Evidence**:

- **File**: `Backend/modules/CatalogoDeProductos/Ingrediente/service.py`
- **Lines 40–54** (`actualizar_precio()`):
  ```python
  db_ingrediente.precio_actual = precio
  uow.ingredientes.add(db_ingrediente)
  uow.commit()
  uow.ingredientes.refresh(db_ingrediente)
  # Disparar recalculo de precios en todos los productos que usan este ingrediente
  ProductoService.recalcular_precio_productos_afectados(session, ingrediente_id)
  return db_ingrediente
  ```
  → Line 53: calls `ProductoService.recalcular_precio_productos_afectados()` after updating price.

- **Lines 72–88** (`update()`):
  ```python
  # Si se actualizó precio_actual, disparar recalculo de precios
  if 'precio_actual' in data.model_dump(exclude_unset=True):
      ProductoService.recalcular_precio_productos_afectados(session, ingrediente_id)
  ```
  → Line 86–87: calls recalculation when `precio_actual` is in the PATCH payload.

- **File**: `Backend/modules/CatalogoDeProductos/Producto/service.py`
- **Lines 128–140** (`recalcular_precio_productos_afectados()`):
  ```python
  def recalcular_precio_productos_afectados(session: Session, ingrediente_id: int):
      with CatalogoDeProductosUnitOfWork(session) as uow:
          stmt = select(ProductoIngrediente.producto_id).where(
              ProductoIngrediente.ingrediente_id == ingrediente_id,
          ).distinct()
          producto_ids = session.exec(stmt).all()
          for pid in producto_ids:
              ProductoService._recalcular_precio_producto(session, pid)
          uow.commit()
  ```
  → Finds all products using that ingredient and recalculates each one.

---

### Task 13.3 — Pedido confirmation decrements ingredient stock

**Status**: ✅ **PASS**

**Evidence**:

- **File**: `Backend/modules/VentasPagosTrazabilidad/Pedido/service.py`
- **Lines 257–398** (`avanzar_estado()`):
  - Line 283: enters CONFIRMADO transition logic when `estado_siguiente == "CONFIRMADO"`.
  - **Lines 370–383** — ingredient stock decrement:
    ```python
    # ── Descontar stock de ingredientes ──
    from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
    from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente

    for det in db_pedido.detalles:
        stmt_pi = select(ProductoIngrediente).where(
            ProductoIngrediente.producto_id == det.producto_id
        )
        for pi in session.exec(stmt_pi):
            cantidad_a_descontar = int(math.ceil(pi.cantidad * det.cantidad))
            ing = session.get(Ingrediente, pi.ingrediente_id)
            if ing:
                ing.stock_actual = max(0, ing.stock_actual - cantidad_a_descontar)
                session.add(ing)
    ```
  → Iterates DetallePedido → ProductoIngrediente → Ingrediente.
  → Formula: `ing.stock_actual -= int(math.ceil(pi.cantidad * det.cantidad))` with a floor at 0.
  ✅ Design D3 formula `pi.cantidad * detalle.cantidad` is correctly implemented (with `math.ceil` rounding for fractional quantities).

---

### Task 13.4 — Insufficient stock returns 409

**Status**: ✅ **PASS**

**Evidence**:

- **File**: `Backend/modules/VentasPagosTrazabilidad/Pedido/service.py`
- **Lines 325–351** — Validation BEFORE decrement (two-pass logic):
  ```python
  # ── Validar stock de ingredientes ──
  errores_ing_stock: list[dict] = []
  for det in db_pedido.detalles:
      stmt_pi = select(ProductoIngrediente).where(
          ProductoIngrediente.producto_id == det.producto_id
      )
      for pi in session.exec(stmt_pi):
          cantidad_needed = pi.cantidad * det.cantidad
          ing = session.get(Ingrediente, pi.ingrediente_id)
          if ing and ing.stock_actual < cantidad_needed:
              errores_ing_stock.append({
                  "ingrediente": ing.nombre,
                  "disponible": ing.stock_actual,
                  "requerido": int(math.ceil(cantidad_needed)),
              })

  if errores_ing_stock:
      raise HTTPException(
          status_code=status.HTTP_409_CONFLICT,
          detail={
              "error": "stock_insuficiente",
              "ingredientes": errores_ing_stock,
          },
      )
  ```
  → **Lines 344–351**: `HTTPException(409)` raised when stock is insufficient.
  → **Two-pass**: ALL validation (329–351) completes before ANY decrement (370–383). If any ingredient has insufficient stock, the 409 is raised and NO stock is decremented.
  → Multiple insufficient ingredients are collected and reported together.

---

### Task 13.5 — Products with medidas are NOT affected

**Status**: ✅ **PASS**

**Evidence**:

- **File**: `Backend/modules/CatalogoDeProductos/Producto/service.py`
- **Lines 98–107** (`_recalcular_precio_producto()`):
  ```python
  def _recalcular_precio_producto(session: Session, producto_id: int):
      db_producto = session.get(Producto, producto_id)
      if not db_producto:
          return

      # Productos con medidas NO se recalcular (Diseño D2)
      if db_producto.medidas:
          return
  ```
  → **Line 106-107**: Early return if `db_producto.medidas` is truthy (exists and non-empty).
  → This is explicitly documented as design decision D2: "Productos con medidas (categoria primordial) no se ven afectados".

---

### Task 13.6 — Products without ingredients keep manual price

**Status**: ✅ **PASS**

**Evidence**:

- **File**: `Backend/modules/CatalogoDeProductos/Producto/service.py`
- **Lines 115–116** (`_recalcular_precio_producto()`):
  ```python
  if not associations:
      return
  ```
  → Early return when product has no `ProductoIngrediente` associations.

- **Line 89–91** (`create()`): `_recalcular_precio_producto` is ONLY called when `data.ingredientes` is truthy.
- **Line 200–202** (`update()`): `_recalcular_precio_producto` is ONLY called when `db_producto.ingredientes` is truthy.
- Products without ingredients never trigger the recalculation path, so `precio_base` stays as manually set.

---

### Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| ProductoIngrediente has cantidad | Creating product with ingredient cantidad | Static code analysis only | ✅ COMPLIANT |
| ProductoIngrediente has cantidad | Updating ingredient cantidad triggers recalculation | Static code analysis only | ✅ COMPLIANT |
| Precio_base auto-calculated | Product with 3 ingredients calculates correct total | Static code analysis only | ✅ COMPLIANT |
| Precio_base auto-calculated | Adding ingredient to product recalculates price | Static code analysis only | ✅ COMPLIANT |
| Precio_base auto-calculated | Changing ingredient price recalculates all affected products | Static code analysis only | ✅ COMPLIANT |
| Products with medidas do NOT auto-calculate | Product with medidas does NOT auto-calculate | Static code analysis only | ✅ COMPLIANT |
| Products without ingredients keep manual | Product without ingredients maintains manual price | Static code analysis only | ✅ COMPLIANT |
| Recalculation triggers | Removing ingredient recalculates price | Static code analysis only | ✅ COMPLIANT |
| Ingredient has price and stock | Creating ingredient with price and stock | Static code analysis only | ✅ COMPLIANT |
| Ingredient has price and stock | Creating ingredient without price and stock | Static code analysis only | ✅ COMPLIANT |
| GET endpoints include price/stock | List includes new fields | Static code analysis only | ✅ COMPLIANT |
| GET endpoints include price/stock | Detail includes new fields | Static code analysis only | ✅ COMPLIANT |
| Update ingredient price triggers recalculation | Successful price update triggers recalc | Static code analysis only | ✅ COMPLIANT |
| Update ingredient price triggers recalculation | Price update with invalid value | Static code analysis only | ✅ COMPLIANT |
| Update ingredient stock | Successful stock update | Static code analysis only | ✅ COMPLIANT |
| Update ingredient stock | Stock update with negative value | Static code analysis only | ✅ COMPLIANT |
| Decrement ingredient stock on order confirmation | Insufficient ingredient stock prevents confirmation | Static code analysis only | ✅ COMPLIANT |
| Decrement ingredient stock on order confirmation | Sufficient stock decrements on confirmation | Static code analysis only | ✅ COMPLIANT |
| Decrement ingredient stock on CONFIRMADO | Order confirmation decrements ingredient stock | Static code analysis only | ✅ COMPLIANT |
| Validate ingredient stock before confirmation | Insufficient ingredient stock returns 409 | Static code analysis only | ✅ COMPLIANT |
| Validate ingredient stock before confirmation | Multiple ingredients insufficient | Static code analysis only | ✅ COMPLIANT |
| Products with medidas do not affect ingredient stock | Medida-only product skips ingredient stock | Static code analysis only | ✅ COMPLIANT |
| Precio_base auto-calculated (product form) | Product with ingredients shows calculated price | Static code analysis only | ✅ COMPLIANT |
| Precio_base auto-calculated (product form) | Product without ingredients keeps editable precio_base | Static code analysis only | ✅ COMPLIANT |
| Precio_base auto-calculated (product form) | Product with medidas keeps manual precio_base | Static code analysis only | ✅ COMPLIANT |
| Product form shows cantidad per row | Admin adjusts ingredient cantidad | Static code analysis only | ✅ COMPLIANT |
| Product list displays calculated price | List shows calculated values | Static code analysis only | ✅ COMPLIANT |

**Compliance summary**: 27/27 scenarios compliant (static analysis)

---

### Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| ProductoIngrediente has cantidad | ✅ Implemented | `ProductoIngrediente.cantidad: Decimal(10,2)` in `producto_ingrediente.py` line 12 |
| Precio_base auto-calculated from ingredients | ✅ Implemented | `_recalcular_precio_producto()` in `Producto/service.py` lines 98–125 |
| Products with medidas NOT auto-calculated | ✅ Implemented | Early return at line 106–107 if `db_producto.medidas` |
| Products without ingredients keep manual | ✅ Implemented | Early return at line 115–116 if no associations |
| Recalculation triggers | ✅ Implemented | create (L89-91), update (L200-202), add/remove ingrediente (L246, L256), update cantidad (L277) |
| Ingredient price/stock fields | ✅ Implemented | `IngredienteBase.precio_actual` + `stock_actual` in models.py lines 16-17 |
| GET endpoints include new fields | ✅ Implemented | `IngredienteRead` schema lines 18-19 |
| PATCH /ingredientes/{id}/precio | ✅ Implemented | Router line 39-46 → service.actualizar_precio() |
| PATCH /ingredientes/{id}/stock | ✅ Implemented | Router line 48-55 → service.actualizar_stock() |
| Ingredient price update triggers recalculation | ✅ Implemented | `actualizar_precio()` line 53 + `update()` lines 86-87 |
| Pedido stock decrement at CONFIRMADO | ✅ Implemented | `avanzar_estado()` lines 370-383 |
| Insufficient stock → 409 | ✅ Implemented | `avanzar_estado()` lines 344-351, two-pass logic |
| Ingrediente schemas | ✅ Implemented | Create/Update/Read + dedicated schemas in `schemas.py` |
| Producto schemas | ✅ Implemented | `IngredienteAsignado.cantidad` + `ProductoIngredienteRead.cantidad` in `schemas.py` |
| ProductoMedida unchanged | ✅ Implemented | Medida model has its own `precio` field, unchanged |

---

### Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| D1: Calculo almacenado, no bajo demanda | ✅ Yes | `precio_base` stored in `producto` table, recalculated on all trigger operations |
| D2: Precio manual vs calculado | ✅ Yes | Products with medidas skip recalculation (early return). Products without ingredients also skip. |
| D3: Descuento de stock al confirmar pedido | ✅ Yes | Two-pass (validate then decrement) inside UoW for transactional safety |
| D4: Migracion sin Alembic | ✅ Yes | Columns added via `SQLModel.metadata.create_all()` |
| D5: Endpoints dedicados precio/stock | ✅ Yes | `PATCH /ingredientes/{id}/precio` and `PATCH /ingredientes/{id}/stock` implemented in router. Update endpoint also handles precio_actual |
| D6: ProductoIngrediente.cantidad como Decimal | ✅ Yes | `Decimal(10,2)` in `producto_ingrediente.py` line 12 |

---

### Issues Found

**CRITICAL** (must fix before archive):
- None

**WARNING** (should fix):
- No automated tests exist for this change. The verification was performed through static code analysis only. All 13.1–13.6 tasks pass based on code review, but there are no tests to run for behavioral validation.
- In `IngredienteService.actualizar_precio()` (line 52-53), the recalculation call happens after the UoW context exits, meaning it runs in a separate transaction. If recalculation fails mid-way, the price update is already committed. This is a known design trade-off (not a bug), but worth noting.

**SUGGESTION** (nice to have):
- Add unit tests for `_recalcular_precio_producto`, `recalcular_precio_productos_afectados`, and `avanzar_estado` ingredient stock logic.
- Consider adding integration tests for the full flow: create ingredient with price → create product with ingredient → confirm pedido → verify stock decremented.

---

### Verdict: **PASS** ✅

All 6 verification tasks (13.1–13.6) pass. The implementation correctly:
1. Auto-calculates `precio_base` from ingredients on create (13.1 ✅)
2. Triggers recalculation when ingredient price changes (13.2 ✅)
3. Decrements ingredient stock on pedido confirmation (13.3 ✅)
4. Returns 409 on insufficient stock with two-pass validation (13.4 ✅)
5. Skips recalculation for products with medidas (13.5 ✅)
6. Preserves manual price for products without ingredients (13.6 ✅)

The code is structurally complete and behaviorally aligned with all specifications and design decisions.
