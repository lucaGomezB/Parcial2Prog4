## ADDED Requirements

### Requirement: BaseRepository provides generic CRUD operations
`BaseRepository[T]` SHALL provide `add()`, `refresh()`, `get_by_id()`, and `get_all()` as generic methods available to all domain repositories. It SHALL accept the model class `T` at instantiation and use it for all queries. For models that extend `SoftDeleteModel`, `get_all()` and `get_by_id()` SHALL automatically filter `deleted_at IS NULL`.

#### Scenario: BaseRepository.add persists an entity
- **WHEN** `repository.add(entity)` is called
- **THEN** the entity SHALL be added to the session (pending commit)

#### Scenario: BaseRepository.refresh loads database-generated fields
- **WHEN** `repository.refresh(entity)` is called after commit
- **THEN** the entity SHALL have its database-generated fields (id, created_at) populated

#### Scenario: BaseRepository.get_by_id returns active entity
- **WHEN** `repository.get_by_id(1)` is called
- **THEN** it SHALL return the entity with id=1 if `deleted_at IS NULL` (for soft-delete models) or the entity regardless (for non-soft-delete models)

#### Scenario: BaseRepository.get_all returns active entities with pagination
- **WHEN** `repository.get_all(skip=0, limit=100)` is called
- **THEN** it SHALL return up to `limit` entities, ordered by id descending, excluding soft-deleted entities (if applicable)

### Requirement: Domain repositories extend BaseRepository
Each domain repository (PedidoRepository, CategoriaRepository, etc.) SHALL inherit from `BaseRepository[T]` and override only domain-specific query methods. Duplicated methods like `add()`, `refresh()`, `get_all()`, `get_by_id()` SHALL be removed from subclasses.

#### Scenario: Duplicated boilerplate is eliminated
- **WHEN** any existing repository is inspected after the refactor
- **THEN** it SHALL NOT contain its own `add()` or `refresh()` methods — these SHALL be inherited from `BaseRepository[T]`

### Requirement: Unit of Work auto-commits on success
All UoW classes SHALL call `self.commit()` in `__exit__` when no exception occurred. This ensures that transactions are not silently lost if a service method omits the explicit `commit()` call.

#### Scenario: UoW commits on normal exit
- **WHEN** a service method exits a `with UoW(session) as uow:` block without exception
- **THEN** the session SHALL be committed automatically

#### Scenario: UoW rollbacks on exception
- **WHEN** a service method raises an exception inside a `with UoW(session) as uow:` block
- **THEN** the session SHALL be rolled back automatically

### Requirement: All modules follow Router → Service → UoW → Repository → Model
Usuario, Rol, and Auth modules SHALL use the Repository + UoW pattern instead of direct `session.add()` / `session.commit()` calls.

#### Scenario: Usuario service uses UoW
- **WHEN** `UsuarioService.crear_usuario()` is called
- **THEN** it SHALL use `IdentidadYAccesoUnitOfWork` and `UsuarioRepository` instead of `session.add()` directly

#### Scenario: Rol service uses UoW
- **WHEN** `RolService.create_rol()` is called
- **THEN** it SHALL use `IdentidadYAccesoUnitOfWork` and `RolRepository` instead of `session.add()` directly

#### Scenario: Auth service uses UoW for refresh tokens
- **WHEN** `AuthService.create_refresh_token()` is called
- **THEN** it SHALL use `IdentidadYAccesoUnitOfWork` and `RefreshTokenRepository` instead of `session.add()` directly

### Requirement: Dead code is removed
The file `modules/Common/uow.py` SHALL be deleted as it is a dead duplicate of `CatalogoDeProductos/uow.py` with broken relative imports.

#### Scenario: Common/uow.py does not exist
- **WHEN** the codebase is inspected after the refactor
- **THEN** `modules/Common/uow.py` SHALL NOT exist
