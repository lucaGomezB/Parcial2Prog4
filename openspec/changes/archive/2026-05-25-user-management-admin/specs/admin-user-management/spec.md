## ADDED Requirements

### Requirement: List users with pagination and role filter
The system SHALL provide a `GET /usuarios/` endpoint that returns a paginated list of users. ADMIN SHALL be able to filter by role code. Each user SHALL include their assigned roles.

#### Scenario: List all users
- **WHEN** ADMIN calls `GET /usuarios/?skip=0&limit=10`
- **THEN** the system SHALL return up to 10 non-deleted users ordered by id DESC
- **THEN** each user SHALL include `id`, `nombre`, `apellido`, `email`, `celular`, and `roles` array

#### Scenario: Filter by role
- **WHEN** ADMIN calls `GET /usuarios/?rol_codigo=CLIENT`
- **THEN** the system SHALL return only users that have the CLIENT role assigned

#### Scenario: Non-admin cannot list users
- **WHEN** a non-ADMIN user calls `GET /usuarios/`
- **THEN** the system SHALL return 403 Forbidden

### Requirement: Get single user with roles
The system SHALL provide a `GET /usuarios/{id}` endpoint.

#### Scenario: Get user by ID
- **WHEN** ADMIN calls `GET /usuarios/1`
- **THEN** the system SHALL return the user with all fields including roles

### Requirement: Update user and roles
The system SHALL provide a `PATCH /usuarios/{id}` endpoint that allows ADMIN to update user fields and reassign roles.

#### Scenario: Update user fields
- **WHEN** ADMIN calls `PATCH /usuarios/1` with `{nombre: "Nuevo"}`
- **THEN** the system SHALL update only the provided fields

#### Scenario: Reassign roles
- **WHEN** ADMIN calls `PATCH /usuarios/1` with `{roles_codigos: ["ADMIN", "CLIENT"]}`
- **THEN** the system SHALL replace all existing roles with the new set
- **THEN** the response SHALL include the updated roles

### Requirement: Soft-delete user
The system SHALL provide a `DELETE /usuarios/{id}` endpoint that performs a soft-delete.

#### Scenario: Soft-delete user
- **WHEN** ADMIN calls `DELETE /usuarios/1`
- **THEN** the system SHALL set `deleted_at` on the user
- **THEN** the user SHALL no longer appear in `GET /usuarios/` results

### Requirement: Admin user management page
The frontend SHALL provide a dedicated `/admin/usuarios` page with user management functionality.

#### Scenario: Page is ADMIN-only
- **WHEN** a non-ADMIN user navigates to `/admin/usuarios`
- **THEN** the system SHALL NOT render the page (ADMIN-only route guard)

#### Scenario: List with pagination and role filter
- **WHEN** ADMIN visits `/admin/usuarios`
- **THEN** the page SHALL display a paginated table of users
- **THEN** a dropdown SHALL allow filtering by role
- **THEN** each row SHALL show nombre, email, role badges, and action buttons

#### Scenario: Edit user
- **WHEN** ADMIN clicks "Editar" on a user
- **THEN** a modal SHALL open with fields: nombre, apellido, email, celular, and a role multi-select
- **WHEN** ADMIN saves
- **THEN** a `PATCH /usuarios/{id}` SHALL be made with the changes

#### Scenario: Delete user
- **WHEN** ADMIN clicks "Eliminar" and confirms
- **THEN** a `DELETE /usuarios/{id}` SHALL be made (soft-delete)
- **THEN** the user SHALL disappear from the list
