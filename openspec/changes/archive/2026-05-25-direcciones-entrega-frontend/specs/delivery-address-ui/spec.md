## ADDED Requirements

### Requirement: API client for delivery addresses
The frontend SHALL provide an API client module with typed methods for all 6 delivery address endpoints.

#### Scenario: Export types match backend schemas
- **WHEN** a developer imports `direccionesApi`
- **THEN** the type `DireccionEntrega` SHALL include all fields: id, usuario_id, alias, linea1, linea2, ciudad, provincia, codigo_postal, es_principal, created_at, updated_at
- **THEN** the method `getAll()` SHALL call `GET /direcciones/`
- **THEN** the method `getById()` SHALL call `GET /direcciones/{id}`
- **THEN** the method `create()` SHALL call `POST /direcciones/`
- **THEN** the method `update()` SHALL call `PATCH /direcciones/{id}`
- **THEN** the method `delete()` SHALL call `DELETE /direcciones/{id}`
- **THEN** the method `setPrincipal()` SHALL call `PATCH /direcciones/{id}/principal`

### Requirement: Delivery address management page
The frontend SHALL provide a dedicated page for users to manage their delivery addresses at the `/direcciones` route.

#### Scenario: List addresses
- **WHEN** a user visits `/direcciones`
- **THEN** the page SHALL display all non-deleted addresses for that user
- **THEN** each address SHALL show alias (if present), linea1, ciudad, and a badge if it's the principal address
- **THEN** addresses SHALL be ordered by es_principal DESC, then created_at DESC

#### Scenario: Create address
- **WHEN** a user clicks "Nueva Dirección" and fills the form
- **THEN** a `POST /direcciones/` SHALL be made with the provided data
- **THEN** the new address SHALL appear in the list

#### Scenario: Edit address
- **WHEN** a user clicks "Editar" on an address row
- **THEN** a form SHALL open pre-filled with the current address data
- **WHEN** the user modifies fields and saves
- **THEN** a `PATCH /direcciones/{id}` SHALL be made with only the changed fields
- **THEN** the list SHALL reflect the changes

#### Scenario: Set principal address
- **WHEN** a user clicks "Marcar como Principal" on a non-principal address
- **THEN** a `PATCH /direcciones/{id}/principal` SHALL be made
- **THEN** the badge SHALL move to the selected address
- **THEN** the list SHALL reorder with the new principal first

#### Scenario: Delete address
- **WHEN** a user clicks "Eliminar" and confirms
- **THEN** a `DELETE /direcciones/{id}` SHALL be made (soft-delete)
- **THEN** the address SHALL disappear from the list

### Requirement: Address selection in cart
The cart page SHALL provide a dropdown to select a delivery address when placing an order.

#### Scenario: Dropdown shows addresses
- **WHEN** the cart page loads and the user has delivery addresses
- **THEN** a dropdown SHALL display each address as `"{alias} — {linea1}, {ciudad}"` (or `"{linea1}, {ciudad}"` if no alias)
- **THEN** the principal address SHALL be preselected in the dropdown
- **THEN** a label "Principal" SHALL appear next to the principal address

#### Scenario: No addresses yet
- **WHEN** the cart page loads and the user has NO delivery addresses
- **THEN** the dropdown SHALL be hidden
- **THEN** a button "Agregar dirección de entrega" SHALL be shown instead

#### Scenario: Create address from cart
- **WHEN** a user clicks "Agregar nueva dirección" in the dropdown or the "Agregar dirección de entrega" button
- **THEN** a modal SHALL open with fields: alias, linea1, linea2, ciudad, provincia, codigo_postal
- **THEN** the user can save to create the address
- **THEN** on success, the dropdown SHALL refresh and select the newly created address

#### Scenario: Address is sent with order
- **WHEN** a user clicks "Realizar Pedido" with a selected address
- **THEN** `direccion_id` SHALL be included in the `POST /pedidos/` payload
- **THEN** `costo_envio` SHALL be set to a non-zero value (indicating delivery)

### Requirement: Navbar link for authenticated users
The navbar SHALL display a "Direcciones" link for authenticated users, between "Menú/Productos" and "Carrito".

#### Scenario: Link visible when authenticated
- **WHEN** a user is authenticated (has a valid JWT token)
- **THEN** the navbar SHALL show a "Direcciones" link
- **WHEN** the user clicks it
- **THEN** they navigate to `/direcciones`

#### Scenario: Link not visible for guests
- **WHEN** a user is not authenticated
- **THEN** the navbar SHALL NOT show a "Direcciones" link

### Requirement: Alias display format
Whenever an address is displayed, the alias SHALL appear before the street address when present.

#### Scenario: Address with alias
- **WHEN** displaying an address with alias="Casa" and linea1="Av. Siempre Viva 123"
- **THEN** the display SHALL be "Casa — Av. Siempre Viva 123"

#### Scenario: Address without alias
- **WHEN** displaying an address with alias=null and linea1="Av. Siempre Viva 123"
- **THEN** the display SHALL be "Av. Siempre Viva 123"
