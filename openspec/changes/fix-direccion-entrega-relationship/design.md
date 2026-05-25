## Context

The `DireccionEntrega` module lives under `modules/IdentidadYAcceso/` and contains a `models.py` with a valid SQLModel table definition (`direcciones_entrega`). However, it is incomplete: no schemas, repository, service, or router exist. Additionally, the `Usuario` model has an incorrect import path that references `Direccion` instead of `DireccionEntrega`, and the model is not registered in `main.py`, so the table is never created.

The existing codebase follows a strict pattern: `models.py -> schemas.py -> repository.py -> service.py -> router.py`, with business logic orchestrated through a Unit of Work (UoW) pattern. The Categoria module under `CatalogoDeProductos` is the canonical example.

The project uses PostgreSQL with SQLModel, JWT auth with RBAC (4 roles: ADMIN, STOCK, PEDIDOS, CLIENT), and soft-delete pattern via `deleted_at`.

## Goals / Non-Goals

**Goals:**
- Fix the broken import path in `Usuario/models.py` that references `..Direccion.models` instead of `..DireccionEntrega.models`.
- Fix nullable fields in `DireccionEntrega/models.py` to match ERD v5 (alias, latitud, longitud should be Optional).
- Build complete CRUD API for DireccionEntrega following the existing project patterns (schemas, repository, service, router).
- Register the model and router in `main.py` so the table is created and endpoints are served.
- Ensure the `es_principal` business rule: at most one principal address per user at any time.

**Non-Goals:**
- Not modifying the Usuario service or router (the relationship via SQLModel is sufficient).
- Not building frontend CRUD pages for addresses (out of scope for this change).
- Not implementing address geolocation or map integration.
- Not changing the existing CatalogoDeProductos patterns or any module outside IdentidadYAcceso.

## Decisions

### Decision 1: Extend IdentidadYAcceso with a Dedicado UoW, not a shared one
- **Choice**: Create `IdentidadYAccesoUnitOfWork` inside `IdentidadYAcceso/uow.py` that aggregates `DireccionEntregaRepository`.
- **Rationale**: The existing `CatalogoDeProductosUnitOfWork` is domain-specific. Mixing identity repositories into it would violate the domain boundary. Each domain owns its UoW.
- **Alternative considered**: Adding DireccionEntrega to a generic `CommonUnitOfWork`. Rejected because it creates circular dependencies and blurs domain boundaries.

### Decision 2: Repository pattern with direct Session, not BaseRepository
- **Choice**: Follow the exact pattern of `CategoriaRepository` — a plain class that receives `Session` in the constructor, without inheriting a `BaseRepository[T]`.
- **Rationale**: The existing codebase does not use a generic `BaseRepository`. Introducing one now would be inconsistent. Consistency trumps DRY in this case.
- **Alternative considered**: Creating a `BaseRepository[T]` with `add`, `get_by_id`, `get_all`, `soft_delete`. Rejected because it would require refactoring all existing repositories.

### Decision 3: Owner scoping via `get_current_user` dependency
- **Choice**: The router will receive the authenticated user via `Depends(get_current_user)` and scope all queries to `usuario_id == current_user.id`. For ADMIN role, skip the scope filter (admins see all).
- **Rationale**: The existing auth dependency already loads the user with eager-loaded roles. Reusing it avoids duplicating auth logic.
- **Alternative considered**: Passing `usuario_id` as a query param. Rejected because it is insecure — any authenticated user could read others' addresses.

### Decision 4: `es_principal` toggle as a dedicated service method, not a generic PATCH field
- **Choice**: Expose `PATCH /direcciones/{id}/principal` as a standalone endpoint that sets `es_principal=true` on the target address and `es_principal=false` on any other address belonging to the same user. The update DTO will NOT include `es_principal` as a mutable field.
- **Rationale**: The business rule "at most one principal per user" requires transactional unset of the old principal. Exposing it as a generic field in `DireccionEntregaUpdate` would allow inconsistent states if the client sets it to false without setting another, or sets multiple to true. The dedicated endpoint is safer and self-documenting.
- **Alternative considered**: Putting the logic in the generic update Service method. Rejected because generic PATCH should be a simple field update; principal management is cross-record business logic.

### Decision 5: Soft-delete returns 204 No Content with no body
- **Choice**: DELETE endpoint returns `HTTP_204_NO_CONTENT` with no body, matching the Producto router pattern.
- **Rationale**: Consistency with the rest of the API. The existing Producto, Categoria, and Ingrediente modules all use 204 for delete.

## Risks / Trade-offs

- **[Risk] Existing data in `database.db`**: If the SQLite database (currently `database.db` in Backend/) has existing data, adding a new table is safe. However, switching to PostgreSQL in production requires running migrations.
  - **Mitigation**: The `SQLModel.metadata.create_all()` call in `lifespan` is idempotent — it creates the table if it does not exist.
- **[Risk] Breaking existing code**: Changing the import path in `Usuario/models.py` could break other modules that indirectly depend on the wrong path.
  - **Mitigation**: Searched the codebase — the only reference to `Direccion` is in `Usuario/models.py` line 9. No other file imports from `..Direccion`.
- **[Trade-off] No Alembic migration**: The current project does not use Alembic (no `alembic/` directory). The `create_all` approach works for development but is not suitable for production schema evolution.
  - **Acceptance**: This is a partial 2 exam project. Alembic setup is a future concern.
- **[Risk] Circular import with Pedido in the future**: `Pedido` will need to import `DireccionEntrega` for the FK relationship, and `Pedido` lives in a different domain (`VentasPagosTrazabilidad`).
  - **Mitigation**: Use `TYPE_CHECKING` guard for type hints (same pattern already used in `Usuario/models.py`).
