## 1. Refactor UsuarioRol y Usuario (IdentidadYAcceso)

- [x] 1.1 Migrar `UsuarioRol` de surrogate PK a PK compuesta `(usuario_id, rol_codigo)` con `usuario_id` FK CASCADE, `rol_codigo` FK SET NULL. Agregar campos `asignado_por_id` (FK Usuario.id, nullable) y `expires_at` (TIMESTAMPTZ, nullable)
- [x] 1.2 Agregar relación 1:N en `Usuario.models`: `pedidos: List["Pedido"] = Relationship(back_populates="usuario")` con TYPE_CHECKING condicional
- [x] 1.3 Actualizar `Usuario.schemas.py` y `Usuario.service.py` si los tipos de relación cambian

## 2. Modelos de catálogo (EstadoPedido, FormaPago)

- [x] 2.1 Crear `EstadoPedido/models.py`: PK semántica `codigo` (VARCHAR(20)), campos `descripcion`, `orden` (INT), `es_terminal` (BOOLEAN). Hereda de `TimestampModel` (sin SoftDeleteModel por ser catálogo)
- [x] 2.2 Crear `EstadoPedido/repository.py`: `get_all()`, `get_by_codigo()` con patrón estándar
- [x] 2.3 Crear `EstadoPedido/schemas.py`: `EstadoPedidoCreate`, `EstadoPedidoRead`, `EstadoPedidoUpdate`
- [x] 2.4 Crear `EstadoPedido/service.py`: CRUD estático con `@staticmethod`, usando UoW
- [x] 2.5 Crear `EstadoPedido/router.py`: endpoints GET públicos, POST/PATCH/DELETE protegidos con `require_roles(["ADMIN"])`
- [x] 2.6 Crear `EstadoPedido/__init__.py` vacío
- [x] 2.7 Crear `FormaPago/models.py`: PK semántica `codigo` (VARCHAR(20)), campos `descripcion`, `habilitado` (BOOLEAN, DEFAULT true). Hereda de TimestampModel
- [x] 2.8 Crear `FormaPago/repository.py`: `get_all(only_habilitados=False)`, `get_by_codigo()`
- [x] 2.9 Crear `FormaPago/schemas.py`: `FormaPagoCreate`, `FormaPagoRead` (con filtro habilitado), `FormaPagoUpdate`
- [x] 2.10 Crear `FormaPago/service.py`: CRUD estático con filtro de habilitados
- [x] 2.11 Crear `FormaPago/router.py`: GET con query param `?incluir_deshabilitadas`, POST/PATCH/DELETE protegidos
- [x] 2.12 Crear `FormaPago/__init__.py` vacío

## 3. Modelo Pedido

- [x] 3.1 Crear `Pedido/models.py`: `PedidoBase(TimestampModel)` con campos `usuario_id` (FK Usuario), `direccion_id` (FK DireccionEntrega, SET NULL), `estado_codigo` (FK EstadoPedido), `forma_pago_codigo` (FK FormaPago), snaps monetarios (`subtotal`, `descuento` DEFAULT 0.00, `costo_envio` DEFAULT 50.00, `total` CHECK >= 0), `notas` (TEXT, nullable). `Pedido(PedidoBase, SoftDeleteModel, table=True)` con relaciones a DetallePedido (CASCADE), HistorialEstadoPedido (CASCADE), Pago, Usuario, DireccionEntrega, EstadoPedido, FormaPago
- [x] 3.2 Crear `Pedido/repository.py`: `get_all(con_filtros)`, `get_by_id()`, `get_by_usuario_id()`
- [x] 3.3 Crear `Pedido/schemas.py`: `PedidoCreate`, `PedidoRead`, `PedidoUpdate` (solo campos editables)
- [x] 3.4 Crear `Pedido/service.py`: CRUD + validación de montos (total = subtotal - descuento + costo_envio)
- [x] 3.5 Crear `Pedido/router.py`: CRUD, GET por usuario autenticado
- [x] 3.6 Crear `Pedido/__init__.py` vacío

## 4. Modelo DetallePedido

- [x] 4.1 Crear `DetallePedido/models.py`: PK compuesta `(pedido_id, producto_id)` con FK CASCADE y RESTRICT respectivamente. Campos: `cantidad` (SMALLINT, CHECK >= 1), `nombre_snapshot` (VARCHAR(200)), `precio_snapshot` (DECIMAL(10,2), CHECK >= 0), `subtotal_snap` (DECIMAL(10,2)), `personalizacion` (Optional[List[int]] mapeado a INTEGER[]). Solo `created_at` (sin updated_at — fila inmutable)
- [x] 4.2 Crear `DetallePedido/repository.py`: `get_by_pedido()`, `add()`
- [x] 4.3 Crear `DetallePedido/schemas.py`: `DetallePedidoCreate`, `DetallePedidoRead`
- [x] 4.4 Crear `DetallePedido/service.py`: lógica de snapshot + cálculo de subtotal
- [x] 4.5 Crear `DetallePedido/__init__.py` vacío

## 5. Modelo HistorialEstadoPedido

- [x] 5.1 Crear `HistorialEstadoPedido/models.py`: `id` (PK), `pedido_id` (FK CASCADE), `estado_desde` (FK EstadoPedido, nullable — RN-02), `estado_hacia` (FK EstadoPedido, NOT NULL), `usuario_id` (FK Usuario, nullable), `motivo` (TEXT, nullable — obligatorio si CANCELADO). Solo `created_at` (append-only, sin updated_at — RN-03)
- [x] 5.2 Crear `HistorialEstadoPedido/repository.py`: solo métodos de lectura + `add()`, sin update/delete
- [x] 5.3 Crear `HistorialEstadoPedido/schemas.py`: `HistorialCreate`, `HistorialRead`
- [x] 5.4 Crear `HistorialEstadoPedido/__init__.py` vacío

## 6. Modelo Pago

- [x] 6.1 Crear `Pago/models.py`: `id` (PK), `pedido_id` (FK), `mp_payment_id` (BIGINT, UQ, nullable), `mp_status` (VARCHAR(30)), `mp_status_detail` (VARCHAR(100), nullable), `external_reference` (VARCHAR(100), UQ), `idempotency_key` (VARCHAR(100), UQ), `transaction_amount` (DECIMAL(10,2)), `payment_method_id` (VARCHAR(50), nullable). Hereda de TimestampModel completo (updated_at se actualiza con webhook)
- [x] 6.2 Crear `Pago/repository.py`: `get_by_pedido()`, `get_by_mp_payment_id()`, `get_by_external_reference()`
- [x] 6.3 Crear `Pago/schemas.py`: `PagoCreate`, `PagoRead`, `PagoUpdate` (solo mp_status y mp_status_detail)
- [x] 6.4 Crear `Pago/__init__.py` vacío

## 7. Unit of Work VentasPagosTrazabilidad

- [x] 7.1 Crear `modules/VentasPagosTrazabilidad/uow.py` con `VentasPagosTrazabilidadUnitOfWork(self, session)` exponiendo repos: `self.estados`, `self.formas_pago`, `self.pedidos`, `self.detalles`, `self.historial`, `self.pagos`. Implementar `__enter__`, `__exit__` (auto-rollback en error), `commit()`, `rollback()`
- [x] 7.2 Crear `modules/VentasPagosTrazabilidad/__init__.py` vacío

## 8. Seed de datos

- [x] 8.1 Agregar `ESTADOS_PEDIDO_SEED` a `scripts/sprint_seed.py` con los 6 estados FSM (PENDIENTE a CANCELADO con sus orden, descripción y es_terminal)
- [x] 8.2 Agregar `FORMAS_PAGO_SEED` a `scripts/sprint_seed.py` con MERCADOPAGO, EFECTIVO, TRANSFERENCIA
- [x] 8.3 Agregar función `seed_estados_pedido()` idempotente en `sprint_seed.py`
- [x] 8.4 Agregar función `seed_formas_pago()` idempotente en `sprint_seed.py`
- [x] 8.5 Invocar ambos seeders en la función `main()` de `sprint_seed.py`
- [x] 8.6 Actualizar `app/db/seed.py` (seed de startup) para incluir EstadoPedido y FormaPago

## 9. Integración en main.py

- [x] 9.1 Importar todos los nuevos modelos en `main.py` para `SQLModel.metadata.create_all()`
- [x] 9.2 Importar y registrar routers: `EstadoPedido.router`, `FormaPago.router`, `Pedido.router`

## 10. Verificación final

- [x] 10.1 Ejecutar `python scripts/sprint_seed.py` y verificar que crea todos los datos sin errores
- [x] 10.2 Verificar que `SQLModel.metadata.create_all()` genera todas las tablas nuevas
- [x] 10.3 Verificar que los endpoints nuevos responden correctamente (requiere iniciar el servidor) ✅ verificado por el usuario — flujo de pedidos funciona correctamente
