## 1. Frontend — API Client

- [x] 1.1 Crear `api/direcciones.ts` con tipos `DireccionEntrega`, `DireccionEntregaInput`, `DireccionEntregaUpdate` y métodos `getAll`, `getById`, `create`, `update`, `delete`, `setPrincipal`

## 2. Frontend — Navbar

- [x] 2.1 Agregar link "Direcciones" en App.tsx para usuarios autenticados (ruta `/direcciones`)

## 3. Frontend — CRUD Page

- [x] 3.1 Crear `pages/DireccionesPage.tsx` con listado de direcciones y badge de principal
- [x] 3.2 Agregar modal/formulario para crear dirección
- [x] 3.3 Agregar modal/formulario para editar dirección
- [x] 3.4 Agregar botón "Marcar como Principal" con llamada a PATCH
- [x] 3.5 Agregar botón "Eliminar" con confirmación y soft-delete

## 4. Frontend — Carrito Integration

- [x] 4.1 Agregar dropdown de selección de dirección en Carrito.tsx con fetch a GET /direcciones/
- [x] 4.2 Preseleccionar dirección principal en el dropdown
- [x] 4.3 Agregar opción "Agregar nueva dirección" en el dropdown con modal inline
- [x] 4.4 Enviar `direccion_id` y `costo_envio` en POST /pedidos/ al crear pedido
- [x] 4.5 Manejar caso sin direcciones (ocultar dropdown, mostrar botón "Agregar dirección")
