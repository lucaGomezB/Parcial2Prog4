## ADDED Requirements

### Requirement: Monetary fields use DECIMAL(10,2) precision
All monetary fields in Pedido, DetallePedido, and Pago SHALL use Python `Decimal` type mapped to SQLAlchemy `Numeric(precision=10, scale=2)`. This ensures exact precision for financial calculations without floating-point rounding errors.

#### Scenario: Pedido monetary fields are Decimal
- **WHEN** inspecting `Pedido.subtotal`, `Pedido.descuento`, `Pedido.costo_envio`, `Pedido.total`
- **THEN** their type SHALL be `Decimal` with `Numeric(precision=10, scale=2)`

#### Scenario: DetallePedido monetary fields are Decimal
- **WHEN** inspecting `DetallePedido.precio_snapshot`, `DetallePedido.subtotal_snap`
- **THEN** their type SHALL be `Decimal` with `Numeric(precision=10, scale=2)`

#### Scenario: Pago monetary field is Decimal
- **WHEN** inspecting `Pago.transaction_amount`
- **THEN** its type SHALL be `Decimal` with `Numeric(precision=10, scale=2)`

#### Scenario: API schemas use Decimal
- **WHEN** inspecting `PedidoCreate`, `PedidoRead`, `DetallePedidoCreate`, `DetallePedidoRead`
- **THEN** their monetary fields SHALL be typed as `Decimal`

#### Scenario: Decimal serializes correctly in API responses
- **WHEN** the API returns a Pedido or DetallePedido
- **THEN** Decimal values SHALL be serialized as standard JSON numbers (Pydantic v2 default behavior)

### Requirement: Hash fields use VARCHAR instead of CHAR
`Usuario.password_hash` and `RefreshToken.token_hash` SHALL use `VARCHAR` (via `max_length`) instead of `CHAR`. This is acceptable because PostgreSQL treats them identically for fixed-length values, and VARCHAR is the project standard.

#### Scenario: password_hash is VARCHAR
- **WHEN** inspecting `Usuario.password_hash`
- **THEN** it SHALL use `max_length=60` (VARCHAR) instead of CHAR(60)

#### Scenario: token_hash is VARCHAR
- **WHEN** inspecting `RefreshToken.token_hash`
- **THEN** it SHALL use `unique=True, max_length=64` (VARCHAR) instead of CHAR(64)

### Requirement: SoftDeleteModel on Ingrediente is preserved
`Ingrediente` SHALL continue to inherit from `SoftDeleteModel` even though the ERD v5 does not explicitly list `deleted_at` for this entity. This is a defensive design choice.

#### Scenario: Ingrediente has soft-delete
- **WHEN** inspecting `Ingrediente.__bases__`
- **THEN** `SoftDeleteModel` SHALL be among its base classes

### Requirement: Extra fields are preserved
Fields not specified in ERD v5 (`tiempo_prep_min` on Producto, `orden_display` on Categoria, `es_principal` and `orden` on ProductoIngrediente) SHALL be preserved as they provide future utility without harming the data model.

#### Scenario: Producto has tiempo_prep_min
- **WHEN** inspecting `Producto.tiempo_prep_min`
- **THEN** it SHALL exist as an integer field with default 0

#### Scenario: Categoria has orden_display
- **WHEN** inspecting `Categoria.orden_display`
- **THEN** it SHALL exist as an integer field with default 0

#### Scenario: ProductoIngrediente has extra fields
- **WHEN** inspecting `ProductoIngrediente.es_principal` and `ProductoIngrediente.orden`
- **THEN** both SHALL exist with their respective defaults
