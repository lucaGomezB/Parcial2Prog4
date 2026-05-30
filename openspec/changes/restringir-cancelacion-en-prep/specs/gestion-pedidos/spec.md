## MODIFIED Requirements

### Requirement: Pedido cancelation rules

The system SHALL enforce role-based restrictions on order cancelation depending on the current order state.

**Affected roles:** CLIENTE (usuario común), ADMIN, PEDIDOS

| Role | PENDIENTE | CONFIRMADO | EN_PREP | EN_CAMINO | ENTREGADO |
|------|-----------|------------|---------|-----------|-----------|
| ADMIN | ✅ | ✅ | ✅ | ✅ | ❌ (terminal) |
| PEDIDOS | ✅ | ✅ | ✅ | ✅ | ❌ (terminal) |
| CLIENTE | ✅ | ✅ | ❌ | ❌ | ❌ (terminal) |

#### Scenario: Client cancels order in PENDIENTE
- **WHEN** a CLIENTE user sends POST /pedidos/{id}/cancelar for a pedido in PENDIENTE state
- **THEN** the system SHALL cancel the order and return 200

#### Scenario: Client cancels order in CONFIRMADO
- **WHEN** a CLIENTE user sends POST /pedidos/{id}/cancelar for a pedido in CONFIRMADO state
- **THEN** the system SHALL cancel the order and return 200

#### Scenario: Client cancels order in EN_PREP
- **WHEN** a CLIENTE user sends POST /pedidos/{id}/cancelar for a pedido in EN_PREP state
- **THEN** the system SHALL return 403 Forbidden and NOT cancel the order

#### Scenario: ADMIN cancels order in EN_PREP
- **WHEN** an ADMIN user sends POST /pedidos/{id}/cancelar for a pedido in EN_PREP state
- **THEN** the system SHALL cancel the order and return 200

#### Scenario: PEDIDOS cancels order in EN_PREP
- **WHEN** a PEDIDOS user sends POST /pedidos/{id}/cancelar for a pedido in EN_PREP state
- **THEN** the system SHALL cancel the order and return 200
