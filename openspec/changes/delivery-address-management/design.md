## Context

El módulo `DireccionEntrega` dentro de `IdentidadYAcceso` ya está implementado con:
- Modelo SQLModel (`DireccionEntrega`) con `alias`, `es_principal`, coordenadas, etc.
- Repository con `get_principal()` y CRUD completo
- Service con `create`, `get_all`, `get_by_id`, `update`, `set_principal`, `soft_delete`
- Router con 6 endpoints: GET list, GET by id, POST create, PATCH update, DELETE soft-delete, PATCH set_principal
- Integrado en `IdentidadYAccesoUnitOfWork`

El módulo `Pedido` en `VentasPagosTrazabilidad` ya tiene `direccion_id` como FK opcional, pero al crear un pedido sin especificar dirección no se auto-selecciona la principal del usuario.

## Goals / Non-Goals

**Goals:**
- Implementar auto-selección de dirección principal en `PedidoService.create()` cuando `direccion_id` no se provea
- Verificar que el CRUD completo de direcciones esté funcional y cumpla con los requisitos
- Documentar el contrato API para consumo del frontend

**Non-Goals:**
- No cambiar la estructura del router `/direcciones` existente
- No agregar nuevos endpoints — los 6 actuales cubren el CRUD completo
- No modificar el modelo de datos (alias, es_principal ya existen)
- No implementar UI del frontend (solo documentación del contrato)

## Decisions

### Decision 1: Ubicación de la lógica de auto-selección
- **Chosen:** Dentro de `PedidoService.create()`, antes de crear el `Pedido` object.
- **Rationale:** Es una responsabilidad de la capa de servicio (orquestación entre módulos). El `PedidoService` ya recibe `session`, y `UsuarioRepository` le permite buscar la dirección principal.
- **Alternatives considered:** En el router — rejected porque el router no debe tener lógica de negocio. En un nuevo servicio de orquestación — rejected por over-engineering para una sola operación.

### Decision 2: Cómo obtener la dirección principal
- **Chosen:** Usar `IdentidadYAccesoUnitOfWork` anidado (o el repo directamente) para obtener `usuario_repo.get_principal_address()`.
- **Rationale:** La dirección principal se obtiene con `DireccionEntregaRepository.get_principal(usuario_id)` que ya existe. El `PedidoService` ya opera con `VentasPagosTrazabilidadUnitOfWork`, pero obtener la dirección principal requiere usar `DireccionEntregaRepository` del módulo IdentidadYAcceso.
- **Implementation:** Se usará una función helper que abre un `IdentidadYAccesoUnitOfWork` solo para la consulta de la dirección principal, antes del UoW de VentasPagosTrazabilidad. Esto evita mezclar UoWs y mantiene cada transacción aislada.

### Decision 3: Comportamiento cuando no hay dirección principal
- **Chosen:** Si el usuario no tiene ninguna dirección marcada como principal, `direccion_id` queda NULL y `costo_envio` es 0 (sin costo de envío).
- **Rationale:** Coincide con el comportamiento actual cuando no se especifica dirección. El frontend debe incentivar al usuario a configurar una dirección antes de pedir.

## Risks / Trade-offs

- **[Risk] UoW anidado**: Obtener la dirección principal requiere un UoW de IdentidadYAcceso, mientras que la creación del Pedido usa VentasPagosTrazabilidadUoW. Esto son dos sesiones distintas, no una transacción atómica. → Mitigation: La lectura de la dirección principal es una operación de solo lectura, no necesita ser transaccional con la creación del pedido. Si el pedido falla después, es seguro porque la lectura ya ocurrió.
- **[Trade-off] No hay endpoint para listar direcciones de otro usuario**: Los endpoints están scoped al usuario autenticado. ADMIN puede ver todas. Esto es por diseño y no cambia.

## API Contract (para frontend)

### Endpoints

| Método | Ruta | Auth | Descripción |
|--------|------|:----:|-------------|
| `GET` | `/direcciones/` | Bearer JWT | Listar direcciones del usuario autenticado |
| `GET` | `/direcciones/{id}` | Bearer JWT | Obtener una dirección por ID |
| `POST` | `/direcciones/` | Bearer JWT | Crear nueva dirección |
| `PATCH` | `/direcciones/{id}` | Bearer JWT | Actualizar campos de dirección (excepto principal) |
| `DELETE` | `/direcciones/{id}` | Bearer JWT | Soft-delete de dirección |
| `PATCH` | `/direcciones/{id}/principal` | Bearer JWT | Marcar/desmarcar como principal |

### Schema `DireccionEntregaCreate`
```json
{
  "alias": "Casa (opcional)",
  "linea1": "Av. Siempre Viva 123",
  "linea2": "Dto 4B (opcional)",
  "ciudad": "Buenos Aires",
  "provincia": "CABA (opcional)",
  "codigo_postal": "1424 (opcional)",
  "latitud": -34.603722 (opcional),
  "longitud": -58.381592 (opcional),
  "es_principal": false
}
```

### Schema `DireccionEntregaRead` (response)
```json
{
  "id": 1,
  "usuario_id": 1,
  "alias": "Casa",
  "linea1": "Av. Siempre Viva 123",
  "linea2": "Dto 4B",
  "ciudad": "Buenos Aires",
  "provincia": "CABA",
  "codigo_postal": "1424",
  "latitud": -34.603722,
  "longitud": -58.381592,
  "es_principal": true,
  "created_at": "2026-05-24T12:00:00Z",
  "updated_at": "2026-05-24T12:00:00Z"
}
```

### Auto-selección en Pedido
- `POST /pedidos/` con `direccion_id: null` → el backend auto-asigna la dirección principal del usuario
- Si no hay dirección principal → `direccion_id: null`, `costo_envio: 0`
