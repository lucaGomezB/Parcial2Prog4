## 1. Backend — Endpoint validar-stock

- [x] 1.1 Crear schema `ValidarStockInput` y `ValidarStockResponse` en `schemas.py` del módulo Pedido
- [x] 1.2 Implementar función `validar_stock_items()` en `PedidoService` que verifique stock sin side effects
- [x] 1.3 Agregar endpoint `POST /pedidos/validar-stock` en `router.py` (requiere auth, abierto a cualquier rol)
- [x] 1.4 Propagar error 409 en auto-advance: cambiar `except Exception: pass` a `except HTTPException: raise` en el create del router

## 2. Frontend — API y tipos

- [x] 2.1 Agregar tipos `ValidarStockInput`, `ValidarStockResponse`, `ValidarStockDetalle` en `api/pedidos.ts`
- [x] 2.2 Agregar función `pedidosApi.validarStock()` en `api/pedidos.ts`

## 3. Frontend — Modal de advertencia de stock

- [x] 3.1 Crear componente `StockWarningModal` inline en `Carrito.tsx` con tabla de items con problema
- [x] 3.2 Implementar lógica de pre-validación: antes de crear pedido, llamar a `validarStock()`
- [x] 3.3 Si hay stock insuficiente, mostrar el modal con inputs para ajustar cantidad y botón "Quitar"
- [x] 3.4 Implementar "Confirmar Cambios": actualizar carrito local + reintentar creación
- [x] 3.5 Manejar error 409 con `stock_insuficiente` desde auto-advance (race condition)

## 4. Frontend — Productos sin stock no agregables

- [x] 4.1 En `ProductosCRUD.tsx`, condicionar el botón "Agregar al carrito" según stock/disponibilidad
- [x] 4.2 Para productos sin medidas: deshabilitar si `stock_cantidad === 0` o `!disponible`
- [x] 4.3 Para productos con medidas: deshabilitar si NINGUNA medida tiene stock > 0 y disponible
- [x] 4.4 Mostrar texto "Sin stock" o "No disponible" según corresponda en el botón deshabilitado
