# Delivery Addresses — API Contract

## Base URL

All endpoints are under `/direcciones`. Authentication via **Bearer JWT** (`Authorization: Bearer <token>`).

## Endpoints

| Method | Path | Auth | Role Access | Description |
|--------|------|:----:|-------------|-------------|
| `GET` | `/direcciones/` | Required | CLIENT (own), ADMIN (all) | List addresses for authenticated user |
| `GET` | `/direcciones/{id}` | Required | CLIENT (own), ADMIN (all) | Get single address by ID |
| `POST` | `/direcciones/` | Required | CLIENT, ADMIN | Create a new address |
| `PATCH` | `/direcciones/{id}` | Required | CLIENT (own), ADMIN (all) | Update address fields (NOT es_principal) |
| `DELETE` | `/direcciones/{id}` | Required | CLIENT (own), ADMIN (all) | Soft-delete an address |
| `PATCH` | `/direcciones/{id}/principal` | Required | CLIENT (own), ADMIN (all) | Toggle address as principal |

## Schemas

### POST /direcciones/ — Request Body

```json
{
  "alias": "Casa (opcional, max 50 chars)",
  "linea1": "Av. Siempre Viva 123 (obligatorio)",
  "linea2": "Dto 4B (opcional)",
  "ciudad": "Buenos Aires (obligatorio)",
  "provincia": "CABA (opcional)",
  "codigo_postal": "1424 (opcional)",
  "latitud": -34.603722 (opcional, decimal 9,6),
  "longitud": -58.381592 (opcional, decimal 9,6),
  "es_principal": false (opcional, default false)
}
```

### PATCH /direcciones/{id} — Request Body

```json
{
  "alias": "Nuevo Alias (opcional)",
  "linea1": "Nueva dirección (opcional)",
  "linea2": "Nuevo dto (opcional)",
  "ciudad": "Nueva ciudad (opcional)",
  "provincia": "Nueva provincia (opcional)",
  "codigo_postal": "Nuevo CP (opcional)",
  "latitud": -34.6 (opcional),
  "longitud": -58.38 (opcional)
}
```

Note: `es_principal` NO se puede cambiar via PATCH. Usar `PATCH /direcciones/{id}/principal`.

### Response — DireccionEntregaRead (all GET, POST, PATCH)

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

### DELETE /direcciones/{id} — Response

`204 No Content` on success. `404 Not Found` if not found or not owned.

### PATCH /direcciones/{id}/principal — Response

Same as `DireccionEntregaRead`. Idempotent: calling twice returns same result.

## Status Codes

| Code | Description |
|:----:|-------------|
| `200` | Success (GET, PATCH) |
| `201` | Created (POST) |
| `204` | No Content (DELETE) |
| `401` | Unauthorized — missing or invalid JWT |
| `403` | Forbidden — authenticated but wrong role |
| `404` | Not found — address doesn't exist or not owned |
| `422` | Validation error — invalid request body |

## Security Rules

1. **Authentication required**: All endpoints require a valid JWT Bearer token.
2. **Owner scoping**: CLIENT users can only access their own addresses. Attempting to access another user's address returns `404` (not `403`) to avoid leaking existence info.
3. **Admin access**: ADMIN users can list, read, update, and delete any address.
4. **Soft-delete**: Deleting an address sets `deleted_at` timestamp. Deleted addresses are excluded from all queries.
5. **Principal constraint**: Only one address per user can be `es_principal=True` at a time. Setting a new principal automatically unsets the previous one.

## Flujo: Crear Pedido con Dirección Principal

1. El usuario crea una o más direcciones via `POST /direcciones/`
2. El usuario marca una como principal via `PATCH /direcciones/{id}/principal`
3. El usuario crea un pedido via `POST /pedidos/` **sin enviar** `direccion_id` (o `null`)
4. El backend automáticamente:
   - Busca la dirección principal del usuario (`es_principal=True`)
   - Si existe, asigna su `id` al pedido como `direccion_id`
   - Si no existe, el pedido queda sin dirección y `costo_envio = 0`
5. El frontend puede leer la dirección asignada en la respuesta del pedido

### Comportamiento detallado

| Escenario | direccion_id enviado | Resultado |
|-----------|:--------------------:|-----------|
| Usuario tiene dirección principal | `null` / no enviado | Se auto-asigna la principal |
| Usuario NO tiene dirección principal | `null` / no enviado | `direccion_id = null`, `costo_envio = 0` |
| Usuario envía dirección específica | `id` válido | Se usa esa dirección (sin importar la principal) |
| Usuario envía dirección de otro | `id` de otro user | Error 404 (el pedido se crea con ese id, pero la FK falla si no existe) |

### Notas para implementación frontend

- **Lista de direcciones**: Al cargar el checkout, llamar a `GET /direcciones/` para obtener todas las direcciones del usuario.
- **Selección de dirección**: Mostrar las direcciones con su `alias` como label. Marcar visualmente la que tiene `es_principal=True`.
- **Cambiar principal**: Implementar un botón/switch que llame a `PATCH /direcciones/{id}/principal`.
- **Alias editable**: El usuario puede cambiar el alias desde la UI llamando a `PATCH /direcciones/{id}` con solo el campo `alias`.
- **Auto-selección**: El formulario de crear pedido puede omitir `direccion_id` si el usuario no selecciona una dirección explícitamente. El backend resolverá la principal.
