## ADDED Requirements

### Requirement: Order history endpoint
The system SHALL provide a `GET /pedidos/historial` endpoint that returns only terminal-state orders (ENTREGADO and CANCELADO), ordered by updated_at DESC.

#### Scenario: Admin views all history
- **WHEN** ADMIN or PEDIDOS calls `GET /pedidos/historial`
- **THEN** the system SHALL return all orders where `estado_codigo` is ENTREGADO or CANCELADO
- **THEN** results SHALL be ordered by `updated_at` descending

#### Scenario: Client views own history
- **WHEN** a CLIENT user calls `GET /pedidos/historial`
- **THEN** the system SHALL return only their orders where `estado_codigo` is ENTREGADO or CANCELADO

### Requirement: Toggle between active and history views
The orders page SHALL provide a tab/button to toggle between "Activos" and "Historial" views.

#### Scenario: Switch to history view
- **WHEN** a user clicks the "Historial" tab on the orders page
- **THEN** the page SHALL load orders from `GET /pedidos/historial`
- **THEN** the page SHALL display "Historial de Pedidos" as the title

#### Scenario: Switch back to active view
- **WHEN** a user clicks the "Activos" tab on the orders page
- **THEN** the page SHALL load orders from `GET /pedidos/activos`
- **THEN** the page SHALL display "Gestión de Pedidos" or "Mis Pedidos" as the title

### Requirement: History rows are read-only
Orders in the history view SHALL NOT show avanzar or cancelar buttons, regardless of user role.

#### Scenario: No action buttons in history
- **WHEN** the history view is active
- **THEN** no "Avanzar" or "Cancelar" buttons SHALL be rendered on any order row
