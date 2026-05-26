## ADDED Requirements

### Requirement: User can manage their delivery addresses
The system SHALL allow an authenticated user to create, read, update, and soft-delete their own delivery addresses. Each address SHALL include: alias (optional), street address (linea1, linea2 optional), city, province (optional), postal code (optional), coordinates (optional lat/lng), and a principal flag.

#### Scenario: Create address
- **WHEN** an authenticated user sends `POST /direcciones/` with valid address data
- **THEN** the system SHALL create the address associated with that user and return the created address with id, timestamps

#### Scenario: List my addresses
- **WHEN** an authenticated user sends `GET /direcciones/`
- **THEN** the system SHALL return all non-deleted addresses belonging to that user, ordered by created_at desc

#### Scenario: Get single address
- **WHEN** an authenticated user sends `GET /direcciones/{id}` for their own address
- **THEN** the system SHALL return the address details

#### Scenario: Update address
- **WHEN** an authenticated user sends `PATCH /direcciones/{id}` with fields to update
- **THEN** the system SHALL update only the provided fields (excluding es_principal)

#### Scenario: Delete address
- **WHEN** an authenticated user sends `DELETE /direcciones/{id}`
- **THEN** the system SHALL soft-delete the address (set deleted_at)

#### Scenario: Unauthorized user cannot manage addresses
- **WHEN** a request is made without a valid JWT token
- **THEN** the system SHALL return 401 Unauthorized

#### Scenario: User cannot access another user's address
- **WHEN** a CLIENT user requests `GET /direcciones/{id}` belonging to a different user
- **THEN** the system SHALL return 404 Not Found

### Requirement: User can set a principal delivery address
The system SHALL allow an authenticated user to mark one address as "principal". Setting a new principal SHALL unset any previously marked principal for that user atomically. The operation SHALL be idempotent.

#### Scenario: Set principal address
- **WHEN** an authenticated user sends `PATCH /direcciones/{id}/principal`
- **THEN** the address SHALL be marked as principal, and any previously principal address for that user SHALL be unmarked

#### Scenario: Idempotent principal
- **WHEN** an authenticated user sends `PATCH /direcciones/{id}/principal` on an already principal address
- **THEN** the address SHALL remain principal (no error)

### Requirement: Principal address is auto-selected when creating a Pedido
When creating a Pedido without providing `direccion_id`, the system SHALL automatically select the user's principal address (the one with `es_principal=True`). If no principal address exists, `direccion_id` SHALL remain NULL and `costo_envio` SHALL be 0.

#### Scenario: Auto-select principal on Pedido creation
- **WHEN** a user creates a Pedido without specifying `direccion_id` AND has a principal address
- **THEN** the Pedido SHALL use the principal address's id as `direccion_id` and apply `costo_envio`

#### Scenario: No principal address exists
- **WHEN** a user creates a Pedido without specifying `direccion_id` AND has NO principal address
- **THEN** the Pedido SHALL have `direccion_id = NULL` and `costo_envio = 0`

### Requirement: Address has an alias field
Each address SHALL support an optional `alias` field (max 50 chars) for user-friendly identification (e.g., "Casa", "Trabajo", "Oficina").

#### Scenario: Create address with alias
- **WHEN** a user creates an address with `alias: "Casa"`
- **THEN** the alias SHALL be stored and returned in the response

#### Scenario: Update alias
- **WHEN** a user sends `PATCH /direcciones/{id}` with `alias: "Nuevo Alias"`
- **THEN** the alias SHALL be updated
