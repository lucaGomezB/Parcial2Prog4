## Context

The project follows a strict unidirectional architecture: `Router → Service → UoW → Repository → Model`. Currently, 10 repositories exist across `CatalogoDeProductos`, `IdentidadYAcceso`, and `VentasPagosTrazabilidad` modules, but all define their methods independently with no shared base class. Three modules (`Usuario`, `Rol`, `Auth`) bypass the pattern entirely, manipulating `session` directly. The `Common/uow.py` file is a dead duplicate of `CatalogoDeProductos/uow.py` with broken imports.

## Goals / Non-Goals

**Goals:**
- Create a generic `BaseRepository[T]` that eliminates boilerplate across all 10+ repositories
- Migrate Usuario, Rol, and Auth/RefreshToken to proper Repository + UoW pattern
- Update all existing repositories to inherit from `BaseRepository[T]`
- Add auto-commit to all UoW `__exit__` methods to prevent silent data loss
- Remove the dead `Common/uow.py` file

**Non-Goals:**
- No new features or API changes — pure refactor with zero behavioral change
- No changes to router layer — all existing endpoints remain identical
- No database schema changes or migrations
- No changes to seed data

## Decisions

### Decision 1: `BaseRepository[T]` location
- **Chosen:** `models/base_repository.py`
- **Rationale:** The existing `models/base.py` already holds `TimestampModel` and `SoftDeleteModel`. Putting the repository base class here keeps all foundational abstractions in one place. Alternative was a `core/` package but that creates a circular dependency risk with `models/`.
- **Alternatives considered:** `core/base_repository.py` — rejected to avoid splitting base abstractions across packages.

### Decision 2: Soft-delete awareness at repository level
- **Chosen:** `BaseRepository[T]` will conditionally filter `deleted_at IS NULL` only if the model is a subclass of `SoftDeleteModel`.
- **Rationale:** Some models (EstadoPedido, FormaPago, Rol) don't have soft-delete. Using `isinstance(model, SoftDeleteModel)` at the class level avoids runtime overhead while keeping the pattern generic.
- **Alternatives considered:** Always filtering `deleted_at IS NULL` — rejected because it breaks non-soft-delete models. Always requiring explicit filter — rejected because it defeats the purpose of a base class.

### Decision 3: UoW auto-commit
- **Chosen:** UoW `__exit__` will call `self.commit()` on success (no exception).
- **Rationale:** Manual `commit()` calls in every service method are fragile — forgetting one causes silent data loss. Auto-commit makes the pattern safe by default. Services can still call `commit()` explicitly if they need early commit, and `__exit__` will no-op on a second commit (SQLAlchemy handles this gracefully).
- **Alternatives considered:** Keep manual commit — rejected because it's error-prone as the codebase grows.

### Decision 4: RefreshTokenRepository in Auth module
- **Chosen:** Create `RefreshTokenRepository` inside `modules/IdentidadYAcceso/Auth/repository.py` rather than a standalone module.
- **Rationale:** RefreshToken is tightly coupled to Auth logic (rotation, validation, cleanup). Keeping the repository in the Auth module maintains cohesion and matches the existing pattern where repositories live inside their domain module.
- **Alternatives considered:** Standalone `RefreshToken` module — rejected as over-engineering for a single repository.

### Decision 5: No RolRepository for pure reads
- **Chosen:** `RolRepository` will be created but its read-only operations (`get_all`, `get_by_codigo`) remain delegated to it. The service layer still orchestrates via UoW even for simple queries.
- **Rationale:** Consistency with the architectural rule. Even if a repository method is a one-liner, maintaining the full `Service → UoW → Repository` chain prevents future shortcuts.

## Risks / Trade-offs

- **Risk: Refactoring Usuario/Auth services may break existing auth flow** → Mitigation: The refactor preserves 100% of the existing logic. The only change is replacing `session.add()` with `repository.add()` inside a UoW context. Test with `POST /auth/login` and `GET /auth/me` after changes.
- **Risk: Circular imports from `models/base_repository.py` importing `SoftDeleteModel` from `models/base.py`** → Mitigation: Both files are in the same `models/` package and have no circular dependency. `base_repository.py` imports from `base.py`, not vice versa.
- **Risk: Auto-commit in UoW could mask errors** → Mitigation: If a service method throws after a `uow.commit()` call, the transaction is already committed. The existing pattern already has this behavior since services call `commit()` explicitly. Auto-commit just adds a safety net for the case where `commit()` is forgotten.
- **Trade-off: BaseRepository[T] adds abstraction overhead** → The overhead is minimal (one extra method call per operation) and the benefit in code reduction across 10+ repositories is significant.
