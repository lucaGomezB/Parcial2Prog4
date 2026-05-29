## ADDED Requirements

### Requirement: Categoria puede marcarse como primordial
El modelo Categoria DEBE tener un campo `es_primordial: bool` con default `False`.
Este campo NO tiene efecto a nivel backend — es solo un indicador para el frontend.

#### Scenario: Admin marca categoría como primordial
- **WHEN** un ADMIN edita una categoría y activa "Es primordial"
- **THEN** el campo `es_primordial` se guarda como `true`
- **THEN** los productos en esa categoría muestran la sección "Medidas" en el formulario

### Requirement: Producto puede tener múltiples medidas
El sistema DEBE permitir definir N medidas por producto, cada una con nombre, precio propio y stock propio.
Los productos SIN medidas DEBEN funcionar exactamente como hoy (backward compatible).

#### Scenario: Admin agrega medidas a un producto
- **WHEN** un ADMIN crea o edita un producto que tiene al menos una categoría primordial
- **THEN** el formulario muestra una sección "Medidas"
- **WHEN** el admin agrega una medida con nombre "500ml", precio 2500, stock 10
- **THEN** la medida se guarda asociada al producto
- **THEN** se puede agregar otra medida "1L" con precio 4000, stock 5

#### Scenario: Producto sin medidas funciona como hoy
- **WHEN** un producto NO tiene ninguna medida asociada
- **THEN** `precio_base` y `stock_cantidad` del producto se usan normalmente
- **THEN** el producto aparece en el catálogo sin selector de medidas
- **THEN** el editor de stock muestra el campo stock_cantidad como siempre

#### Scenario: Producto con medidas ignora precio_base y stock_cantidad
- **WHEN** un producto tiene al menos una medida
- **THEN** `precio_base` se IGNORA (se usa precio de cada medida)
- **THEN** `stock_cantidad` se IGNORA (se usa stock de cada medida)
- **THEN** `disponible` es `true` si al menos una medida tiene stock > 0

### Requirement: Admin puede editar o eliminar medidas
El sistema DEBE permitir actualizar nombre, precio, stock y orden de una medida existente.
También DEBE permitir eliminar una medida.

#### Scenario: Admin edita precio de una medida
- **WHEN** un ADMIN cambia el precio de "500ml" de 2500 a 2600
- **THEN** el precio se actualiza
- **THEN** los pedidos futuros usan el nuevo precio (pedidos existentes no se modifican)

#### Scenario: Admin elimina una medida
- **WHEN** un ADMIN elimina la medida "250ml"
- **THEN** la medida se borra de la BD
- **THEN** el producto queda con las medidas restantes
- **THEN** si no quedan medidas, el producto vuelve a usar precio_base y stock_cantidad

### Requirement: API REST para medidas
El sistema DEBE exponer endpoints REST para CRUD de medidas, anidados bajo producto.

#### Scenario: Listar medidas de un producto
- **WHEN** se hace GET /productos/{id}/medidas/
- **THEN** retorna array de medidas con id, nombre, precio, stock, orden
- **THEN** retorna array vacío si el producto no tiene medidas

#### Scenario: Crear medida
- **WHEN** se hace POST /productos/{id}/medidas/ con nombre, precio, stock
- **THEN** retorna la medida creada con su id
- **THEN** SOLO accessible para ADMIN

#### Scenario: Error al crear medida sin nombre
- **WHEN** se hace POST /productos/{id}/medidas/ sin nombre
- **THEN** retorna 422 Validation Error
