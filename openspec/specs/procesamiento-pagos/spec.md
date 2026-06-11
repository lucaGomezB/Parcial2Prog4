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

### Requirement: Approved payment triggers CONFIRMADO

When a pending payment is approved via webhook, an order that is in PENDIENTE state SHALL be eligible for automatic advancement to CONFIRMADO. The PedidoService SHALL support a `confirmar_si_pagado()` method that checks if the most recent Pago for the order has mp_status="approved" and, if so, advances the state to CONFIRMADO. The existing `avanzar_estado()` flow SHALL create a Pago record (with mp_status="pending") when the order uses forma_pago_codigo="MERCADOPAGO".

#### Scenario: MP payment creation at CONFIRMADO transition
- **WHEN** avanzar_estado() transitions an order to CONFIRMADO
- **AND** the order uses forma_pago_codigo="MERCADOPAGO"
- **THEN** the system creates a Pago record with mp_status="pending"

#### Scenario: Non-MP orders skip payment creation
- **WHEN** avanzar_estado() transitions an order to CONFIRMADO
- **AND** the order uses forma_pago_codigo="EFECTIVO"
- **THEN** no Pago record is created

### Requirement: Display payment status in PedidosPage

The frontend SHALL display each order's payment status when viewing pedidos. The Pedido response SHALL include `pagos` data showing `mp_status` for the most recent payment attempt.

#### Scenario: Payment status shown in pedido list
- **WHEN** a user views their pedidos
- **THEN** each pedido shows its payment status (if any) next to the order state
