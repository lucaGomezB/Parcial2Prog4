## 1. Auto-selección de dirección principal en Pedido

- [x] 1.1 Modificar `PedidoService.create()` para que, si `data.direccion_id` es None, busque la dirección principal del usuario via `DireccionEntregaRepository.get_principal()` y la asigne automáticamente
- [x] 1.2 Verificar que `costo_envio` se aplique correctamente cuando se auto-asigna una dirección (vs costo_envio=0 cuando no hay dirección)

## 2. Verificación del CRUD de direcciones

- [x] 2.1 Confirmar que `POST /direcciones/` funciona con y sin `alias`, con y sin `es_principal`
- [x] 2.2 Confirmar que `PATCH /direcciones/{id}` actualiza `alias` correctamente
- [x] 2.3 Confirmar que `PATCH /direcciones/{id}/principal` es idempotente y atómico
- [x] 2.4 Confirmar que `DELETE /direcciones/{id}` hace soft-delete (deleted_at != NULL)
- [x] 2.5 Confirmar que `GET /direcciones/` excluye direcciones soft-deleteadas

## 3. Seguridad y ownership

- [x] 3.1 Confirmar que un usuario CLIENT no puede ver/editar/borrar direcciones de otro usuario
- [x] 3.2 Confirmar que ADMIN puede ver todas las direcciones

## 4. Documentación para frontend

- [x] 4.1 Extraer el contrato API completo (endpoints, schemas request/response, códigos HTTP) y dejarlo en `docs/api/delivery-addresses.md`
- [x] 4.2 Documentar el flujo de "crear pedido con dirección principal" para el frontend
