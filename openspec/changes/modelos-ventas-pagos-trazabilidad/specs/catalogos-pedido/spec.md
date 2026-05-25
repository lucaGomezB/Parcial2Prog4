## ADDED Requirements

### Requirement: Sistema gestiona catálogo de estados de pedido

El sistema SHALL mantener un catálogo `EstadoPedido` con PK semántica `codigo` (VARCHAR(20)) que contenga los 6 estados FSM: PENDIENTE, CONFIRMADO, EN_PREP, EN_CAMINO, ENTREGADO, CANCELADO. Cada estado tiene `descripcion`, `orden` (1-6) y `es_terminal` (boolean). El seed SHALL ser idempotente.

#### Scenario: Catálogo se crea con seed
- **WHEN** se ejecuta `python scripts/sprint_seed.py`
- **THEN** la tabla `estadopedido` contiene exactamente 6 filas con los códigos PENDIENTE, CONFIRMADO, EN_PREP, EN_CAMINO, ENTREGADO, CANCELADO
- **THEN** ENTREGADO y CANCELADO tienen `es_terminal = true`
- **THEN** los órdenes son 1, 2, 3, 4, 5, 6 respectivamente

#### Scenario: Seed es idempotente
- **WHEN** se ejecuta el seed dos veces
- **THEN** la tabla `estadopedido` sigue teniendo exactamente 6 filas

### Requirement: Sistema gestiona catálogo de formas de pago

El sistema SHALL mantener un catálogo `FormaPago` con PK semántica `codigo` (VARCHAR(20)) que contenga 3 métodos: MERCADOPAGO, EFECTIVO, TRANSFERENCIA. Cada forma tiene `descripcion` y `habilitado` (boolean, default true). El seed SHALL ser idempotente.

#### Scenario: Catálogo se crea con seed
- **WHEN** se ejecuta `python scripts/sprint_seed.py`
- **THEN** la tabla `formapago` contiene exactamente 3 filas con los códigos MERCADOPAGO, EFECTIVO, TRANSFERENCIA
- **THEN** las tres tienen `habilitado = true`

#### Scenario: Forma de pago deshabilitada no aparece en checkout
- **WHEN** `habilitado = false` para una forma de pago
- **THEN** el endpoint GET /formas-pago no la incluye en la respuesta
- **THEN** el endpoint GET /formas-pago?incluir_deshabilitadas=true la incluye
