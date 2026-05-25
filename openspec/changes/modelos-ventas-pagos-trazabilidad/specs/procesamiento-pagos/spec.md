## ADDED Requirements

### Requirement: Sistema registra pagos con triple unique

El sistema SHALL registrar pagos con `pedido_id`, `mp_payment_id` (nullable, unique), `mp_status` (VARCHAR(30)), `external_reference` (unique, UUID que identifica al pedido en MP), `idempotency_key` (unique, UUID del backend que evita cobros duplicados), `transaction_amount` (DECIMAL(10,2)), y `payment_method_id` (VARCHAR(50), nullable). Timestamps con created_at y updated_at.

#### Scenario: Creación de pago exitoso
- **WHEN** se registra un pago con external_reference e idempotency_key únicos
- **THEN** el pago se crea con mp_status = "pending"

#### Scenario: Idempotency key evita duplicados
- **WHEN** se intenta crear un segundo pago con la misma idempotency_key
- **THEN** el sistema rechaza con error de integridad (400)

#### Scenario: Actualización por webhook
- **WHEN** llega un webhook IPN que cambia mp_status de "pending" a "approved"
- **THEN** el pago actualiza su mp_status y mp_status_detail
- **THEN** updated_at se actualiza automáticamente

### Requirement: Pago referencia a Pedido

Cada pago SHALL tener `pedido_id` como FK a Pedido.id, permitiendo múltiples intentos de pago por pedido.

#### Scenario: Múltiples intentos de pago
- **WHEN** un pedido tiene 2 pagos fallidos (rejected) y 1 exitoso (approved)
- **THEN** los 3 registros existen en la tabla pago
- **THEN** el pedido referencia al pago aprobado para su estado CONFIRMADO
