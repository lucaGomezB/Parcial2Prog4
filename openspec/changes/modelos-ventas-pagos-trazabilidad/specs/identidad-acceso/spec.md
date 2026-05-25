## ADDED Requirements

### Requirement: Usuario tiene relación 1:N con Pedido

El modelo Usuario SHALL tener una relación `pedidos: List[Pedido]` con back_populates, reflejando que un usuario puede tener muchos pedidos.

#### Scenario: Usuario puede tener múltiples pedidos
- **WHEN** se consulta un usuario con pedidos
- **THEN** la relación retorna la lista de pedidos del usuario
- **THEN** la relación es lazy por defecto

### Requirement: UsuarioRol usa PK compuesta con campos extendidos

La tabla `UsuarioRol` SHALL usar PK compuesta `(usuario_id, rol_codigo)` en lugar de surrogate id. SHALL incluir `asignado_por_id` (FK a Usuario.id, nullable = auto-asignación sistema) y `expires_at` (TIMESTAMPTZ, nullable). `rol_codigo` SHALL ser obligatorio (NOT NULL).

#### Scenario: PK compuesta previene duplicados
- **WHEN** se intenta asignar el mismo rol al mismo usuario dos veces
- **THEN** el sistema rechaza con error de integridad (400)

#### Scenario: Asignación por otro usuario
- **WHEN** un ADMIN asigna un rol a otro usuario
- **THEN** asignado_por_id = ID del ADMIN
- **THEN** la relación queda registrada correctamente

#### Scenario: Rol con expiración
- **WHEN** se asigna un rol con expires_at en el pasado
- **THEN** el sistema trata el rol como expirado (no se considera activo)
