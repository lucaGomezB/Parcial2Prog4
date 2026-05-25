## Why

The `DireccionEntrega` module was left incomplete after the first partial. It has a valid SQLModel model definition but:
- The import path in `Usuario/models.py` references a non-existent module (`Direccion` instead of `DireccionEntrega`), which will cause a `ModuleNotFoundError` at runtime when the relationship is resolved.
- The module lacks schemas, repository, service, and router, making it impossible for clients to create, read, update, or delete delivery addresses via the API.
- The model itself has nullable fields (`alias`, `latitud`, `longitud`) typed as non-optional, which conflicts with the ERD v5 specification and can cause silent data inconsistencies.
- The model is not registered in `main.py`, so SQLModel will not create the `direcciones_entrega` table automatically.

This blocks the Pedido module (Dominio 3) because `Pedido.direccion_id` is a FK to `DireccionEntrega.id`.

## What Changes

- **Fix import path**: Change `from ..Direccion.models import DireccionEntrega` to `from ..DireccionEntrega.models import DireccionEntrega` in `Usuario/models.py`.
- **Fix model nullability**: Make `alias`, `latitud`, and `longitud` fields `Optional` in `DireccionEntrega/models.py` to match ERD v5.
- **Build full CRUD module**: Create `schemas.py` (Pydantic request/response schemas), `repository.py` (data access with soft-delete and user-scoped queries), `service.py` (business logic including the `es_principal` toggle), and `router.py` (REST endpoints with RBAC).
- **Register in app**: Import `DireccionEntrega` model and router in `main.py` so the table is created by SQLModel metadata and endpoints are exposed.
- **Unit of Work**: Create `IdentidadYAccesoUnitOfWork` aggregating `UsuarioRepository` and `DireccionEntregaRepository` transactions.

## Capabilities

### New Capabilities
- `direccion-entrega-crud`: Full CRUD for delivery addresses, scoped to the authenticated user. Includes:
  - Create a new address for the current user.
  - List all addresses for the current user (soft-delete filtered).
  - Get single address by ID (owner-scoped).
  - Update address fields.
  - Soft-delete an address.
  - Toggle `es_principal` (ensures at most one principal address per user).
  - Set `es_principal=true` on creation (auto-unset any existing principal).
- `identidad-acceso-uow`: Unit of Work that wraps Usuario and DireccionEntrega repositories in a single transaction context.

### Modified Capabilities
- (none)

## Impact

- **Files modified**:
  - `Backend/modules/IdentidadYAcceso/Usuario/models.py` (import path fix)
  - `Backend/modules/IdentidadYAcceso/DireccionEntrega/models.py` (field nullability fix)
  - `Backend/main.py` (register model + router)
- **Files created**:
  - `Backend/modules/IdentidadYAcceso/DireccionEntrega/__init__.py`
  - `Backend/modules/IdentidadYAcceso/DireccionEntrega/schemas.py`
  - `Backend/modules/IdentidadYAcceso/DireccionEntrega/repository.py`
  - `Backend/modules/IdentidadYAcceso/DireccionEntrega/service.py`
  - `Backend/modules/IdentidadYAcceso/DireccionEntrega/router.py`
  - `Backend/modules/IdentidadYAcceso/uow.py`
- **API changes**:
  - New prefix: `/direcciones` with tags `["Direcciones de Entrega"]`
  - Endpoints: `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}`, `PATCH /{id}/principal`
  - All endpoints require authentication (`CLIENT` or `ADMIN`)
  - Admin can view/update any address; CLIENT only their own
- **Database**: New table `direcciones_entrega` will be created by SQLModel metadata (already defined in models.py, was just not registered).
