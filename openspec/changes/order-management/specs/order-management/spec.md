## ADDED Requirements

### Requirement: FSM state transitions validated in service
The system SHALL enforce a Finite State Machine for order states. Transitions are validated in the service layer, never in the router.

Valid transitions:
- PENDIENTE → CONFIRMADO
- CONFIRMADO → EN_PREP
- EN_PREP → EN_CAMINO
- EN_CAMINO → ENTREGADO
- Any non-terminal state → CANCELADO

#### Scenario: Valid transition
- **WHEN** a user calls avanzar on an order in CONFIRMADO state
- **THEN** the order SHALL transition to EN_PREP
- **THEN** a new HistorialEstadoPedido SHALL be created with estado_desde=CONFIRMADO, estado_hacia=EN_PREP

#### Scenario: Invalid transition
- **WHEN** a user calls avanzar on an order in ENTREGADO state
- **THEN** the system SHALL return an error

### Requirement: Cancel order
ADMIN and PEDIDOS SHALL be able to cancel any active order. Regular users SHALL only cancel orders with state before EN_CAMINO.

#### Scenario: Admin cancels any order
- **WHEN** an ADMIN user calls cancelar on any active order
- **THEN** the order SHALL transition to CANCELADO

#### Scenario: User cancels before EN_CAMINO
- **WHEN** a regular user calls cancelar on their own order in CONFIRMADO or EN_PREP state
- **THEN** the order SHALL transition to CANCELADO

#### Scenario: User cannot cancel after EN_CAMINO
- **WHEN** a regular user calls cancelar on their own order in EN_CAMINO or later state
- **THEN** the system SHALL return an error

### Requirement: Audit trail (HistorialEstadoPedido)
Each state transition SHALL create an INSERT-only record in HistorialEstadoPedido. No UPDATE or DELETE operations on this table.

#### Scenario: Transition creates history record
- **WHEN** a state transition occurs
- **THEN** a new HistorialEstadoPedido row SHALL be inserted with estado_desde, estado_hacia, usuario_id, and created_at

### Requirement: Active orders filter
The system SHALL provide an endpoint that returns only non-terminal orders (excluding ENTREGADO and CANCELADO), ordered by created_at DESC.

#### Scenario: Active orders list
- **WHEN** ADMIN or PEDIDOS calls GET /pedidos/activos
- **THEN** the system SHALL return all orders where estado_codigo is not ENTREGADO or CANCELADO
- **THEN** results SHALL be ordered by created_at descending

### Requirement: Order creation from cart
The "Realizar Pedido" button in the cart SHALL create an order and advance it to CONFIRMADO state.

#### Scenario: Create order from cart
- **WHEN** a user clicks "Realizar Pedido" with items in the cart
- **THEN** a new Pedido SHALL be created with DetallePedido snapshots for each item
- **THEN** the order SHALL advance to CONFIRMADO state
- **THEN** the cart SHALL be cleared

### Requirement: Order details popup
Each order row SHALL have a button to view order details in a popup modal showing DetallePedido items with product name, quantity, unit price, and subtotal.

#### Scenario: View order details
- **WHEN** a user clicks "Ver Detalles" on an order
- **THEN** a modal SHALL display all DetallePedido items with nombre_snapshot, cantidad, precio_snapshot, and subtotal_snap

### Requirement: Role-based visibility
ADMIN and PEDIDOS SHALL access the orders page and see all orders. Regular users SHALL only see their own orders via /mis-pedidos. The avanzar and cancelar buttons SHALL be visible based on role.

#### Scenario: Admin sees all orders
- **WHEN** ADMIN user visits the orders page
- **THEN** they SHALL see all active orders from all users
- **THEN** they SHALL have avanzar and cancelar buttons

#### Scenario: Regular user sees own orders
- **WHEN** a CLIENT user visits /mis-pedidos
- **THEN** they SHALL only see their own orders
- **THEN** they SHALL have a cancel button (if before EN_CAMINO) but no avanzar button
