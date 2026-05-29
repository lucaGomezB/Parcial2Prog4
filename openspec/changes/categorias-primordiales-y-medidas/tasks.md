## 1. Backend — Modelo ProductoMedida + campo Categoria

- [x] 1.1 Crear modelo `ProductoMedida` en `CatalogoDeProductos/Producto/models.py` (id, producto_id FK, nombre, precio Decimal(10,2), stock int, orden int, TimestampModel)
- [x] 1.2 Agregar `es_primordial: bool = False` al modelo `Categoria`
- [x] 1.3 Agregar `medida_snapshot: Optional[str]` al modelo `DetallePedido`
- [x] 1.4 Agregar relación `Producto.medidas: List[ProductoMedida]` con `selectinload` y cascade="all, delete-orphan"
- [x] 1.5 Crear `ProductoMedidaCreate` y `ProductoMedidaRead` schemas en `Producto/schemas.py`
- [x] 1.6 Agregar `medidas: List[ProductoMedidaCreate] = []` opcional a `ProductoCreate`
- [x] 1.7 Actualizar `ProductoRead` para incluir `medidas: List[ProductoMedidaRead]`
- [x] 1.8 Actualizar `CategoriaRead` para incluir `es_primordial`
- [x] 1.9 Actualizar `CategoriaCreate` y `CategoriaUpdate` para incluir `es_primordial`

## 2. Backend — CRUD de Medidas (endpoints + service)

- [x] 2.1 Crear `ProductoMedidaRepository` en `CatalogoDeProductos/Producto/repository.py`
- [x] 2.2 Agregar métodos al `ProductoService`: `listar_medidas`, `crear_medida`, `actualizar_medida`, `eliminar_medida`
- [x] 2.3 Agregar router `GET /productos/{producto_id}/medidas/` (solo ADMIN)
- [x] 2.4 Agregar router `POST /productos/{producto_id}/medidas/` (solo ADMIN)
- [x] 2.5 Agregar router `PATCH /productos/{producto_id}/medidas/{id}` (solo ADMIN)
- [x] 2.6 Agregar router `DELETE /productos/{producto_id}/medidas/{id}` (solo ADMIN)
- [x] 2.7 Al crear/actualizar producto, manejar `medidas` en el payload: reemplazar todas las medidas si se envía el array
- [x] 2.8 Actualizar lógica de `disponible` del producto: si tiene medidas, `true` si alguna tiene stock > 0

## 3. Backend — Stock por medida al confirmar pedido

- [x] 3.1 En `PedidoService.avanzar_estado()`, al transicionar a CONFIRMADO: si el detalle tiene `medida_id`, descontar stock de `ProductoMedida.stock`
- [x] 3.2 Si el detalle NO tiene `medida_id`, descontar de `Producto.stock_cantidad` como hoy
- [x] 3.3 Validar que la `ProductoMedida` existe al crear el pedido (rechazar con 400 si no)
- [x] 3.4 Actualizar `DetallePedidoInput` schema para incluir `medida_id: Optional[int]`

## 4. Frontend — API module + tipos

- [x] 4.1 Agregar tipos `ProductoMedida`, `ProductoMedidaCreate` en `api/productos.ts`
- [x] 4.2 Agregar métodos `getMedidas`, `createMedida`, `updateMedida`, `deleteMedida` al `productosApi`
- [x] 4.3 Actualizar `ProductoCreate` y `Producto` interfaces para incluir `medidas`

## 5. Frontend — Formulario de Producto (crear/editar)

- [x] 5.1 En `ProductosCRUD.tsx`, detectar si las categorías seleccionadas incluyen alguna con `es_primordial = true`
- [x] 5.2 Si sí, mostrar sección "Medidas" dentro del formulario (arriba de los botones)
- [x] 5.3 Sección medidas: tabla con nombre, precio, stock, botón quitar + botón "Agregar medida"
- [x] 5.4 Al agregar medida: inputs inline para nombre, precio, stock
- [x] 5.5 Al enviar el formulario (crear/editar), incluir `medidas` en el payload
- [x] 5.6 Al cargar edición de producto existente, precargar sus medidas en la tabla

## 6. Frontend — Editor de Stock adaptado

- [x] 6.1 En el modo "Editar Stock" (`START_STOCK_EDIT`), detectar si el producto tiene medidas
- [x] 6.2 Si tiene medidas: mostrar tabla inline con nombre de medida y campo stock editable por cada una
- [x] 6.3 Si no tiene medidas: mantener el input de `stock_cantidad` como hoy

## 7. Frontend — Selector de medidas en Catálogo/Carrito

- [x] 7.1 Al cargar productos en la tabla del catálogo, incluir `medidas` en el response
- [x] 7.2 Modificar botón "Agregar al carrito": si el producto tiene medidas, abrir modal de selección
- [x] 7.3 Modal de selección: lista de medidas con radio button, precio, stock disponible, cantidad
- [x] 7.4 Actualizar `CarritoItem` en `utils/carrito.ts` para incluir `medidaId` y `medidaNombre`
- [x] 7.5 Actualizar `addToCart()` para aceptar medida opcional
- [x] 7.6 Si mismo producto con distinta medida → items separados en el carrito
- [x] 7.7 Mostrar medida en la lista del carrito (`Carrito.tsx`)

## 8. Frontend — Detalle de pedido muestra medida

- [x] 8.1 Actualizar `DetallePedido` interface en `api/pedidos.ts` para incluir `medida_snapshot`
- [x] 8.2 En `PedidosPage.tsx`, mostrar columna "Medida" o texto inline si `medida_snapshot` existe

## 9. Frontend — Categorías CRUD (flag es_primordial)

- [x] 9.1 En `CategoriasCRUD.tsx`, agregar checkbox "Es primordial" en el formulario de crear/editar categoría
- [x] 9.2 Enviar `es_primordial` al crear/actualizar categoría
- [x] 9.3 Mostrar badge "Primordial" en la tabla de categorías si corresponde

## 10. Seed + DB

- [x] 10.1 Ejecutar backend para que SQLModel cree la nueva tabla `ProductoMedida` y columnas
- [x] 10.2 Actualizar `seed.py`: marcar Bebidas, Tartas, Pizzas como `es_primordial = true`
- [x] 10.3 Agregar productos con medidas de ejemplo: Coca Cola (250ml/$1500/stock10, 500ml/$2500/stock5, 1L/$4000/stock2), Pizza Muzzarella (1 porción/$3000/stock20, entera/$12000/stock5), Tarta Jamón y Queso (1 porción/$2500/stock15, media/$7000/stock8, entera/$12000/stock3)
- [x] 10.4 Resetear BD y ejecutar seed para verificar que todo funciona
