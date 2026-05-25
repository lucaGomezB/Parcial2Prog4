## 1. Bug Fixes (Model Layer)

- [x] 1.1 Fix import path in `Usuario/models.py`: change `from ..Direccion.models import DireccionEntrega` to `from ..DireccionEntrega.models import DireccionEntrega`
- [x] 1.2 Fix nullable fields in `DireccionEntrega/models.py`: make `alias`, `latitud`, and `longitud` `Optional` to match ERD v5

## 2. DireccionEntrega Schemas

- [x] 2.1 Create `DireccionEntrega/schemas.py` with `DireccionEntregaCreate` (includes `es_principal`), `DireccionEntregaUpdate` (excludes `es_principal`), `DireccionEntregaRead`
- [x] 2.2 Ensure all schemas use `from_attributes = True` Config for ORM mode

## 3. DireccionEntrega Repository

- [x] 3.1 Create `DireccionEntrega/repository.py` with `DireccionEntregaRepository` class
- [x] 3.2 Implement `add()`, `flush()`, `refresh()` methods (following CategoriaRepository pattern)
- [x] 3.3 Implement `get_by_id()` with soft-delete filter (`deleted_at IS NULL`)
- [x] 3.4 Implement `get_by_usuario()` to return all non-deleted addresses for a user, ordered by `es_principal DESC, created_at DESC`
- [x] 3.5 Implement `get_principal()` to find the current principal address for a user (used by toggle logic)
- [x] 3.6 Implement `get_all()` with optional `usuario_id` filter (admin view)

## 4. IdentidadYAcceso Unit of Work

- [x] 4.1 Create `IdentidadYAcceso/uow.py` with `IdentidadYAccesoUnitOfWork` class
- [x] 4.2 Wire `DireccionEntregaRepository` into the UoW (following CatalogoDeProductosUnitOfWork pattern)
- [x] 4.3 Implement `__enter__`, `__exit__`, `commit()`, `rollback()` methods

## 5. DireccionEntrega Service

- [x] 5.1 Create `DireccionEntrega/service.py` with `DireccionEntregaService` class (static methods)
- [x] 5.2 Implement `create()`: validate data, handle `es_principal=True` (auto-unset existing principal), use UoW for atomicity
- [x] 5.3 Implement `get_all()` with optional `usuario_id` scope
- [x] 5.4 Implement `get_by_id()` with ownership validation
- [x] 5.5 Implement `update()`: exclude `es_principal`, partial update via `model_dump(exclude_unset=True)`
- [x] 5.6 Implement `set_principal()`: find and unset old principal, set new principal, all in one UoW transaction
- [x] 5.7 Implement `soft_delete()`: set `deleted_at` via UoW

## 6. DireccionEntrega Router

- [x] 6.1 Create `DireccionEntrega/router.py` with `APIRouter(prefix="/direcciones", tags=["Direcciones de Entrega"])`
- [x] 6.2 Implement `POST /` - create address (requires auth, returns 201)
- [x] 6.3 Implement `GET /` - list addresses for current user (ADMIN sees all)
- [x] 6.4 Implement `GET /{id}` - get address by ID with ownership check (404 for non-owned)
- [x] 6.5 Implement `PATCH /{id}` - update address (excludes `es_principal`)
- [x] 6.6 Implement `DELETE /{id}` - soft-delete address (returns 204)
- [x] 6.7 Implement `PATCH /{id}/principal` - toggle principal address (dedicated endpoint)
- [x] 6.8 Use `Depends(get_current_user)` for auth and role-based scoping in service layer

## 7. Register in main.py

- [x] 7.1 Import `DireccionEntrega` model from `modules.IdentidadYAcceso.DireccionEntrega.models` so SQLModel metadata creates the table
- [x] 7.2 Import and include `direccion_router` from `modules.IdentidadYAcceso.DireccionEntrega.router`

## 8. Verify

- [x] 8.1 Start the server and verify the `direcciones_entrega` table is created
- [x] 8.2 Test full CRUD flow via API: POST, GET list, GET by id, PATCH, PATCH principal, DELETE (10/10 PASSED)
- [x] 8.3 Verify owner scoping: CLIENT user cannot read/update/delete another user's address (404 scoping PASSED)
- [x] 8.4 Verify admin bypass: ADMIN can read any address (PASSED via admin tests)
- [x] 8.5 Verify principal uniqueness: creating two addresses with `es_principal=true` leaves only the last one as principal (PASSED)
- [x] 8.6 Verify the import fix: Usuario model loads without ModuleNotFoundError
