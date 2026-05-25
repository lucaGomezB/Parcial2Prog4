# DireccionEntrega CRUD

## ADDED Requirements

### Requirement: Create delivery address
The system SHALL allow an authenticated user to create a new delivery address associated with their account.

**Schema:**
- `alias`: VARCHAR(50), optional. Human label like "Casa", "Trabajo".
- `linea1`: TEXT, required. Street address line 1.
- `linea2`: TEXT, optional. Street address line 2.
- `ciudad`: VARCHAR(100), required.
- `provincia`: VARCHAR(100), optional.
- `codigo_postal`: VARCHAR(10), optional.
- `latitud`: DECIMAL(9,6), optional.
- `longitud`: DECIMAL(9,6), optional.
- `es_principal`: BOOLEAN, optional, defaults to false. If set to true, any existing principal address for this user SHALL be automatically unset within the same transaction.

#### Scenario: Successful creation
- **WHEN** an authenticated user POSTs valid address data to `/direcciones`
- **THEN** the system creates a new address with `usuario_id` set to the authenticated user's ID, returns HTTP 201 with the created address

#### Scenario: Creation with es_principal=true replaces existing principal
- **WHEN** a user already has an address with `es_principal=true` and creates a new address with `es_principal=true`
- **THEN** the old address's `es_principal` is set to `false` and the new address has `es_principal=true`, all within a single transaction

#### Scenario: Unauthenticated creation fails
- **WHEN** an unauthenticated user POSTs to `/direcciones`
- **THEN** the system returns HTTP 401 Unauthorized

### Requirement: List addresses for current user
The system SHALL return all non-deleted addresses belonging to the authenticated user, ordered by `es_principal` DESC then `created_at` DESC.

#### Scenario: User lists their addresses
- **WHEN** an authenticated user GETs `/direcciones`
- **THEN** the system returns HTTP 200 with an array of their non-deleted addresses, principal address first

#### Scenario: Admin lists all addresses
- **WHEN** an ADMIN user GETs `/direcciones`
- **THEN** the system returns HTTP 200 with all non-deleted addresses across all users

### Requirement: Get single address by ID
The system SHALL return a single non-deleted address by its ID, scoped to the authenticated user's own addresses (unless ADMIN).

#### Scenario: User retrieves own address
- **WHEN** an authenticated user GETs `/direcciones/{id}` where the address belongs to them
- **THEN** the system returns HTTP 200 with the address data

#### Scenario: User retrieves another user's address
- **WHEN** an authenticated CLIENT user GETs `/direcciones/{id}` where the address belongs to a different user
- **THEN** the system returns HTTP 404 Not Found (no information about ownership leaked)

#### Scenario: Retrieve non-existent address
- **WHEN** a user GETs `/direcciones/{id}` with an ID that does not exist or is soft-deleted
- **THEN** the system returns HTTP 404 Not Found

### Requirement: Update delivery address
The system SHALL allow updating editable fields of an existing address. Editable fields: `alias`, `linea1`, `linea2`, `ciudad`, `provincia`, `codigo_postal`, `latitud`, `longitud`. The `es_principal` field SHALL NOT be updatable via this endpoint (use the dedicated principal toggle endpoint instead).

#### Scenario: Successful update
- **WHEN** an authenticated user PATCHes `/direcciones/{id}` with valid fields
- **THEN** the system updates only the provided fields and returns HTTP 200 with the updated address

#### Scenario: Update non-owned address
- **WHEN** a CLIENT user PATCHes `/direcciones/{id}` belonging to another user
- **THEN** the system returns HTTP 404 Not Found

#### Scenario: Attempt to update es_principal via generic PATCH
- **WHEN** a user includes `es_principal` in the PATCH body
- **THEN** the system ignores the field (it is not in the update schema)

### Requirement: Toggle principal address
The system SHALL provide a dedicated endpoint to set an address as the principal address. Setting `es_principal=true` on one address SHALL atomically unset `es_principal` on any other address belonging to the same user.

#### Scenario: Set principal address
- **WHEN** an authenticated user sends `PATCH /direcciones/{id}/principal`
- **THEN** the system sets `es_principal=true` on that address, sets `es_principal=false` on any other address of the same user that was previously principal, and returns HTTP 200

#### Scenario: Set principal on already-principal address
- **WHEN** a user sends `PATCH /direcciones/{id}/principal` on the address that is already principal
- **THEN** the system returns HTTP 200 with no changes (idempotent)

### Requirement: Soft-delete delivery address
The system SHALL soft-delete an address by setting its `deleted_at` timestamp.

#### Scenario: Successful soft-delete
- **WHEN** an authenticated user DELETEs `/direcciones/{id}` on their own address
- **THEN** the system sets `deleted_at` to current UTC time and returns HTTP 204 No Content

#### Scenario: Delete non-owned address
- **WHEN** a CLIENT user DELETEs `/direcciones/{id}` belonging to another user
- **THEN** the system returns HTTP 404 Not Found

### Requirement: Owner scoping for CLIENT role
The system SHALL enforce that CLIENT users can only access their own addresses. ADMIN users SHALL have unrestricted access to all addresses.

#### Scenario: CLIENT cannot see other user addresses
- **WHEN** a CLIENT user accesses any address endpoint with an ID belonging to another user
- **THEN** the system responds as if the address does not exist (HTTP 404)

#### Scenario: ADMIN can see any address
- **WHEN** an ADMIN user accesses any address endpoint with any valid address ID
- **THEN** the system returns the address data regardless of ownership
