## Why

Actualmente las direcciones de entrega solo existen en el backend (API completa con 6 endpoints). El usuario no tiene interfaz para gestionar sus direcciones ni puede seleccionar una dirección al hacer un pedido desde el carrito. Se necesita el frontend completo para que los usuarios puedan crear, editar, listar y eliminar sus direcciones, y seleccionar una al realizar un pedido.

## What Changes

- Crear frontend API layer (`api/direcciones.ts`) con tipos y métodos para los 6 endpoints existentes
- Crear página de gestión de direcciones (`pages/DireccionesPage.tsx`) con CRUD completo:
  - Listado de direcciones con alias, dirección y badge de "Principal"
  - Modal/formulario para crear nueva dirección
  - Modal/formulario para editar dirección existente
  - Botón para marcar como principal (PATCH /{id}/principal)
  - Botón para eliminar (soft-delete con confirmación)
- Agregar link "Direcciones" en el navbar para usuarios autenticados
- Modificar `Carrito.tsx` para agregar un selector desplegable de direcciones:
  - Mostrar las direcciones del usuario con alias + línea1
  - Tener preseleccionada la dirección principal
  - Opción "Agregar nueva dirección" al final del dropdown
  - Al seleccionar/cambiar, actualizar direccion_id y costo_envio en el create payload
- Agregar `direccion_id` al `CreatePedidoInput` en el frontend
- Alias se muestra antes que la dirección (ej: "Casa — Av. Siempre Viva 123")

## Capabilities

### New Capabilities
- `delivery-address-ui`: Interfaz de usuario para gestionar direcciones de entrega (CRUD completo, selección en carrito)

### Modified Capabilities
- (`delivery-address` existente en `openspec/changes/delivery-address-management/`): No se modifican requisitos del backend. Solo se agrega UI que consume los endpoints existentes.

## Impact

- **Frontend**: 2 páginas nuevas (DireccionesPage, modales) + modificaciones a Carrito.tsx + navbar en App.tsx + nuevo API client
- **Backend**: Sin cambios. Todo el backend ya está implementado y funcional.
- **API**: Sin cambios. Se consumen los endpoints existentes.
