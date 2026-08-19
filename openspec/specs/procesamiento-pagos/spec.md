## Requirements

### Requirement: Sistema registra pagos con triple unique

El sistema SHALL registrar pagos con `pedido_id`, `mp_payment_id` (nullable, unique), `mp_status` (VARCHAR(30)), `external_reference` (unique, UUID que identifica al pedido en MP), `idempotency_key` (unique, UUID del backend que evita cobros duplicados), `transaction_amount` (DECIMAL(10,2)), y `payment_method_id` (VARCHAR(50), nullable). Timestamps con created_at y updated_at.

#### Scenario: Creacion de pago exitoso
- **WHEN** se registra un pago con external_reference e idempotency_key unicos
- **THEN** el pago se crea con mp_status = "pending"

#### Scenario: Idempotency key evita duplicados
- **WHEN** se intenta crear un segundo pago con la misma idempotency_key
- **THEN** el sistema rechaza con error de integridad (400)

#### Scenario: Actualizacion por webhook
- **WHEN** llega un webhook IPN que cambia mp_status de "pending" a "approved"
- **THEN** el pago actualiza su mp_status y mp_status_detail
- **THEN** updated_at se actualiza automaticamente

### Requirement: Pago referencia a Pedido

Cada pago SHALL tener `pedido_id` como FK a Pedido.id, permitiendo multiples intentos de pago por pedido.

#### Scenario: Multiples intentos de pago
- **WHEN** un pedido tiene 2 pagos fallidos (rejected) y 1 exitoso (approved)
- **THEN** los 3 registros existen en la tabla pago
- **THEN** el pedido referencia al pago aprobado para su estado CONFIRMADO

### Requirement: Pago pedido_id becomes nullable

The `Pago.pedido_id` column SHALL be changed from `NOT NULL` to nullable. The field SHALL be populated only after the Pedido is created (at webhook time for MP, at creation time for PAGO_LOCAL/EFECTIVO). All existing queries that join Pago to Pedido SHALL handle NULL `pedido_id` gracefully.

#### Scenario: Pago created without pedido_id
- **WHEN** `init-from-cart` creates a new Pago record
- **THEN** `pedido_id` is NULL
- **AND** the record is valid and can be retrieved

#### Scenario: Pago backfilled after Pedido creation
- **WHEN** the webhook creates a Pedido from a snapshot
- **AND** backfills `pago.pedido_id = <new_pedido_id>`
- **THEN** the Pago record now has a valid pedido_id FK
- **AND** `GET /pagos/{pedido_id}` returns the payment

### Requirement: Initiate MercadoPago payment from cart (replaces init_mp_payment)

The system SHALL provide `POST /pagos/init-from-cart` that accepts cart items, validates stock, creates a `carrito_snapshot`, creates a Pago record with `mp_status="pending"`, creates a MercadoPago preference, and returns the `init_point` URL. The Pago record's `pedido_id` SHALL be NULL at creation time (no Pedido exists yet). The `PagoService.init_from_cart` method SHALL replace the previous `init_mp_payment(pedido_id)` flow.

#### Scenario: Successful payment initiation from cart
- **WHEN** a user with 3 items in cart calls `POST /pagos/init-from-cart` with subtotal=150.00 and direccion_id=3
- **THEN** the system validates stock for all 3 items
- **AND** a `carrito_snapshot` is created with the cart items and totals
- **AND** a `Pago` record is created with `mp_status="pending"`, `pedido_id=NULL`, `external_reference=<uuid>`
- **AND** a MercadoPago preference is created with all cart items as line items
- **AND** the response contains `{ pago: PagoRead, init_point: "https://..." }`

#### Scenario: Stock insufficient at init time
- **WHEN** `POST /pagos/init-from-cart` is called with an item exceeding available stock
- **THEN** the system returns HTTP 409 with `{ error: "stock_insuficiente", detalles: [...] }`
- **AND** no Pago record is created
- **AND** no snapshot is created

#### Scenario: Idempotency prevents duplicate init
- **WHEN** the same cart data is submitted twice in rapid succession
- **AND** a pending Pago already exists for this user with the same cart fingerprint
- **THEN** the system returns the existing Pago and init_point (no duplicate)

### Requirement: Webhook creates Pedido from snapshot

The `PagoService.process_webhook()` method SHALL, when payment status is `approved`, look up the `carrito_snapshot` by `external_reference`, call `PedidoService.crear_desde_snapshot()` to create the Pedido, backfill `pago.pedido_id`, delete the snapshot, and broadcast `pago_confirmado` with the new `pedido_id`. The method SHALL NOT call `confirmar_por_pago()` (which is now dead code for the MP flow).

#### Scenario: Approved payment creates Pedido
- **WHEN** a MP webhook arrives with `mp_status="approved"` for external_reference=X
- **THEN** the handler finds the Pago and snapshot by external_reference=X
- **AND** calls `PedidoService.crear_desde_snapshot(snapshot)` which validates stock, deducts stock, creates Pedido + DetallePedido rows
- **AND** the snapshot is deleted in the same UoW
- **AND** `pago.pedido_id` is set to the new Pedido's ID
- **AND** after UoW commit, `pago_confirmado` is broadcast with `pedido_id`

#### Scenario: Rejected payment does NOT create Pedido
- **WHEN** a MP webhook arrives with `mp_status="rejected"`
- **THEN** the Pago status is updated to "rejected"
- **AND** no Pedido is created
- **AND** the cart_snapshot is preserved (user can retry from cart)

#### Scenario: Duplicate webhook is idempotent
- **WHEN** a second webhook arrives with the same `external_reference` after Pedido already created
- **THEN** the snapshot lookup returns None (already deleted)
- **AND** the handler returns early without creating a duplicate Pedido
- **AND** HTTP 200 is returned

#### Scenario: Stock insufficient at webhook time
- **WHEN** a webhook arrives for an approved payment but stock is now insufficient
- **THEN** `crear_desde_snapshot()` raises a stock_insuficiente error inside the UoW
- **AND** the transaction rolls back (snapshot preserved, Pago status updated to "approved" with a `stock_error` flag)
- **AND** the error is logged for manual resolution

### Requirement: Display payment status in PedidosPage

The frontend SHALL display each order's payment status when viewing pedidos. The Pedido response SHALL include `pagos` data showing `mp_status` for the most recent payment attempt.

#### Scenario: Payment status shown in pedido list
- **WHEN** a user views their pedidos
- **THEN** each pedido shows its payment status (if any) next to the order state

### Requirement: Payment Webhook Broadcasts Pago Confirmado (REQ-PP-005)

The system SHALL broadcast a `pago_confirmado` event when a payment webhook confirms a payment and advances the associated order to CONFIRMADO. The system SHALL broadcast to the pedido-specific room AND the admin room. The system SHALL use the same post-commit broadcast pattern: compute and commit the payment transition inside the UoW block, then broadcast after `__exit__`.

#### Scenario: Approved payment triggers broadcast

- **Given** a Mercado Pago webhook arrives with `mp_status: "approved"` for pedido 42
- **When** the payment is confirmed and `avanzar_estado` transitions pedido 42 to CONFIRMADO
- **Then** a `pago_confirmado` event is broadcast to room `42`
- **And** the event is also broadcast to the admin room via `broadcast_admin`
- **And** the payload includes `"event": "pago_confirmado"`, `"estado_anterior": "PENDIENTE"`, `"estado_nuevo": "CONFIRMADO"`

#### Scenario: Payment not approved does not broadcast

- **Given** a Mercado Pago webhook arrives with `mp_status: "rejected"` for pedido 42
- **When** the webhook is processed
- **Then** no `pago_confirmado` broadcast occurs
- **And** the order state is not advanced

#### Scenario: Broadcast occurs after UoW commit

- **Given** a payment webhook with `mp_status: "approved"` is being processed
- **When** the payment transition and order advancement execute inside `with uow`
- **Then** no broadcast call occurs inside the `with` block
- **And** the broadcast fires only after `uow.__exit__` commits the transaction

#### Scenario: WSManager not available

- **Given** the Pago service is instantiated without a `ws_manager`
- **When** a payment is confirmed
- **Then** the payment processing completes normally
- **And** no broadcast is attempted and no error is raised

### Requirement: Webhook endpoint validates x-signature header

The `POST /pagos/webhook` endpoint SHALL validate the `x-signature` HTTP header using HMAC-SHA256 with the `MP_WEBHOOK_SECRET` environment variable. The raw request body SHALL be used as the HMAC message. Requests without a valid signature SHALL receive HTTP 403.

#### Scenario: Valid signature accepted
- **WHEN** a webhook request arrives with header `x-signature: <valid-hmac>`
- **AND** `HMAC-SHA256(request.body.raw, MP_WEBHOOK_SECRET) == <valid-hmac>`
- **THEN** the request SHALL proceed to `PagoService.process_webhook()`
- **AND** the response SHALL be HTTP 200

#### Scenario: Missing x-signature header rejected
- **WHEN** a webhook request arrives WITHOUT an `x-signature` header
- **THEN** the endpoint SHALL return HTTP 403 with detail `{"error": "signature_missing"}`
- **AND** the request body SHALL NOT be processed

#### Scenario: Invalid signature rejected
- **WHEN** a webhook request arrives with header `x-signature: <invalid-hmac>`
- **AND** `HMAC-SHA256(request.body.raw, MP_WEBHOOK_SECRET) != <invalid-hmac>`
- **THEN** the endpoint SHALL return HTTP 403 with detail `{"error": "invalid_signature"}`
- **AND** the request body SHALL NOT be processed

#### Scenario: Sandbox placeholder secret
- **WHEN** `MP_WEBHOOK_SECRET` is the placeholder value `"your-webhook-secret-here"`
- **THEN** the endpoint SHALL log a WARNING once at startup
- **AND** the endpoint SHALL still validate signatures (failing validation is expected behavior)
- **AND** a clear log message SHALL indicate: "MP_WEBHOOK_SECRET is a placeholder -- webhook auth will fail until configured with a real secret"

#### Scenario: Raw body preserved for signature validation
- **WHEN** a webhook request arrives
- **THEN** the router SHALL read the raw body via `await request.body()` BEFORE calling `request.json()`
- **AND** the raw body bytes SHALL be passed to the signature validation function
- **AND** the parsed JSON SHALL be passed to `PagoService.process_webhook()`
