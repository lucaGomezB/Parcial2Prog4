## 1. BaseRepository foundation

- [x] 1.1 Create `models/base_repository.py` with `BaseRepository[T]` class providing `add()`, `refresh()`, `get_by_id()`, `get_all()`, and conditional soft-delete filtering
- [x] 1.2 Update all 10 existing repositories to inherit from `BaseRepository[T]` and remove duplicated `add()`/`refresh()`/`get_all()`/`get_by_id()` methods

## 2. UoW auto-commit

- [x] 2.1 Add auto-commit on success in `__exit__` for `CatalogoDeProductosUnitOfWork` (modules/CatalogoDeProductos/uow.py)
- [x] 2.2 Add auto-commit on success in `__exit__` for `IdentidadYAccesoUnitOfWork` (modules/IdentidadYAcceso/uow.py)
- [x] 2.3 Add auto-commit on success in `__exit__` for `VentasPagosTrazabilidadUnitOfWork` (modules/VentasPagosTrazabilidad/uow.py)

## 3. Usuario repository + UoW migration

- [x] 3.1 Create `UsuarioRepository` in `modules/IdentidadYAcceso/Usuario/repository.py` extending `BaseRepository[Usuario]`
- [x] 3.2 Refactor `modules/IdentidadYAcceso/Usuario/service.py` to use `IdentidadYAccesoUnitOfWork` with `UsuarioRepository` instead of direct `session.add()`/`session.commit()`
- [x] 3.3 Add `UsuarioRepository` to `IdentidadYAccesoUnitOfWork`

## 4. Rol repository + UoW migration

- [x] 4.1 Create `RolRepository` in `modules/IdentidadYAcceso/Rol/repository.py` extending `BaseRepository[Rol]` with `get_by_codigo()` domain method
- [x] 4.2 Refactor `modules/IdentidadYAcceso/Rol/service.py` to use `IdentidadYAccesoUnitOfWork` with `RolRepository` instead of direct `session.add()`/`session.commit()`
- [x] 4.3 Add `RolRepository` to `IdentidadYAccesoUnitOfWork`

## 5. Auth/RefreshToken repository + UoW migration

- [x] 5.1 Create `RefreshTokenRepository` in `modules/IdentidadYAcceso/Auth/repository.py` extending `BaseRepository[RefreshToken]` with `get_by_hash()`, `get_expired()` domain methods
- [x] 5.2 Refactor `modules/IdentidadYAcceso/Auth/service.py` to use `IdentidadYAccesoUnitOfWork` with `RefreshTokenRepository` instead of direct `session.add()`/`session.commit()`/`session.delete()`
- [x] 5.3 Add `RefreshTokenRepository` to `IdentidadYAccesoUnitOfWork`

## 6. Cleanup

- [x] 6.1 Delete `modules/Common/uow.py` (dead duplicate)
- [x] 6.2 Verify all module imports work after refactor (15 repos + 3 UoWs)
- [x] 6.3 Delete dead `modules/Common/uow.py` duplicate
