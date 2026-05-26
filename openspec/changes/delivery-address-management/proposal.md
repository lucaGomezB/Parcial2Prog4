## Why

El módulo `DireccionEntrega` ya tiene CRUD completo (modelo, repository, service, router, schemas, UoW) pero falta una feature crítica de UX: al crear un pedido sin especificar dirección, el sistema debe auto-seleccionar la dirección principal del usuario. Además, se necesita documentar el contrato API para que el frontend pueda consumir direcciones de entrega correctamente.

## What Changes

- Agregar auto-selección de dirección principal en `PedidoService.create()` cuando no se envíe `direccion_id`
- Verificar y asegurar que el CRUD completo de direcciones esté funcional y correcto (GET, POST, PATCH, DELETE, set_principal)
- Verificar que el campo `alias` funcione correctamente en create/update
- NO hay cambios en el router existente — la API ya expone `/direcciones` con todos los endpoints necesarios

## Capabilities

### New Capabilities
- `delivery-address`: Gestión completa de direcciones de entrega del usuario autenticado. Cubre CRUD, alias, selección de dirección principal y auto-selección al crear pedidos.

### Modified Capabilities
_(No existing specs to modify)_

## Impact

- **Backend/modules/VentasPagosTrazabilidad/Pedido/service.py**: Modificar `create()` para auto-seleccionar dirección principal del usuario si no se provee `direccion_id`
- **Backend/modules/IdentidadYAcceso/DireccionEntrega/**: Sin cambios (CRUD ya completo)
- **Frontend**: Se tomarán notas del contrato API completo para implementación futura
