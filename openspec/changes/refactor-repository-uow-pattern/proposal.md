## Why

The project enforces a strict unidirectional architecture: `Router → Service → UoW → Repository → Model`. Three modules (Usuario, Rol, Auth) currently bypass this pattern by working directly with `session.add()`/`session.commit()` instead of going through a Repository + Unit of Work. Additionally, there is no `BaseRepository[T]` base class, causing code duplication across all 10 existing repositories, and a dead duplicate file (`Common/uow.py`) that would crash if imported. This needs to be fixed to maintain consistency and ensure future modules follow the correct pattern.

## What Changes

- Create a generic `BaseRepository[T]` base class with common CRUD operations (`add`, `refresh`, `get_all`, `get_by_id`, soft-delete support)
- Migrate **Usuario** to `UsuarioRepository` + integrate into `IdentidadYAccesoUnitOfWork`
- Migrate **Rol** to `RolRepository` + integrate into `IdentidadYAccesoUnitOfWork`
- Migrate **Auth/RefreshToken** to `RefreshTokenRepository` + integrate into `IdentidadYAccesoUnitOfWork`
- Refactor existing repository classes to inherit from `BaseRepository[T]` and remove duplicated code
- Fix `IdentidadYAccesoUnitOfWork` to auto-commit on success in `__exit__`
- Delete the dead `Common/uow.py` duplicate file

## Capabilities

### New Capabilities
- `repository-pattern`: Generic base repository and UoW infrastructure. Covers `BaseRepository[T]`, consistent UoW auto-commit behavior, and elimination of code duplication across all repositories.

### Modified Capabilities
_(No existing specs to modify — no prior spec files in `openspec/specs/`)_

## Impact

- **Backend/modules/IdentidadYAcceso/Usuario/**: New `repository.py`, refactored `service.py` to use UoW
- **Backend/modules/IdentidadYAcceso/Rol/**: New `repository.py`, refactored `service.py` to use UoW
- **Backend/modules/IdentidadYAcceso/Auth/**: New `repository.py` (RefreshToken), refactored `service.py` to use repository
- **Backend/modules/IdentidadYAcceso/uow.py**: Add UsuarioRepository, RolRepository, RefreshTokenRepository; add auto-commit on `__exit__`
- **Backend/modules/Common/uow.py**: **DELETE** (dead duplicate of CatalogoDeProductosUoW)
- **Backend/models/**: New `base_repository.py` with `BaseRepository[T]`
- **All 10 existing repository classes**: Refactor to inherit from `BaseRepository[T]`
