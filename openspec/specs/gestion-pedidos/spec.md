# Spec: gestion-pedidos (delta)

## MODIFIED Requirements

### Requirement: Pedido listing shows order ID to all authenticated users

The PedidosPage SHALL display a "Pedido #" column in the DataTable for all authenticated users regardless of role (CLIENTE, STOCK, PEDIDOS, ADMIN). The column SHALL render the pedido ID in a monospace font as `#{pedido.id}` and SHALL be sortable.

The detail popup title SHALL include the pedido ID as `Detalles del Pedido #{pedido.id}` for all authenticated users regardless of role.

The "Usuario" column (showing the order owner's email) SHALL remain visible only to ADMIN and PEDIDOS roles.

#### Scenario: CLIENTE sees order IDs in their order list

- **WHEN** a user with CLIENTE role views the "Mis Pedidos" (activos or historial) page
- **THEN** the DataTable includes a "Pedido #" column showing `#123` (monospace) for each row
- **AND** the column is sortable by `id`

#### Scenario: CLIENTE sees order ID in the detail popup title

- **WHEN** a CLIENTE user clicks "Ver Detalles" on a pedido
- **THEN** the modal title displays `Detalles del Pedido #123`
- **AND** the modal content (products, totals, timeline) renders correctly

#### Scenario: ADMIN and PEDIDOS still see the ID column (no regression)

- **WHEN** a user with ADMIN or PEDIDOS role views the pedidos page
- **THEN** the "Pedido #" column is visible (unchanged behavior)
- **AND** the "Usuario" column remains visible (unchanged behavior)

#### Scenario: STD role visibility is determined by role check

- **WHEN** a user with STOCK role views pedidos (if such access exists)
- **THEN** the "Pedido #" column is visible
- **AND** the "Usuario" column is visible only if the column definition uses `esGestor` guard
