## Why

Actualmente no existe una interfaz de administración de usuarios. El backend solo tiene `POST /usuarios/` para crear usuarios. El ADMIN no puede listar, buscar, modificar roles ni eliminar usuarios. Se necesita una página completa de gestión de usuarios accesible solo por ADMIN.

## What Changes

- **Backend**: Agregar 4 endpoints al módulo `Usuario` existente:
  - `GET /usuarios/` — Listado paginado con filtro opcional por rol (`?rol_codigo=ADMIN`), cada usuario incluye sus roles
  - `GET /usuarios/{id}` — Obtener un usuario con sus roles
  - `PATCH /usuarios/{id}` — Actualizar datos del usuario (nombre, apellido, email, celular) y/o re-asignar roles
  - `DELETE /usuarios/{id}` — Soft-delete del usuario (setea `deleted_at`)

- **Frontend**: Nueva página `/admin/usuarios` accesible solo por ADMIN:
  - Listado paginado con filtro por rol (dropdown con todos los roles)
  - Cada fila muestra: nombre, email, roles (badges), acciones
  - Modal para editar datos + roles del usuario
  - Botón para soft-delete con confirmación
  - Botón para crear nuevo usuario (reutiliza el endpoint POST existente)

## Capabilities

### New Capabilities
- `admin-user-management`: Gestión completa de usuarios (CRUD + roles) exclusiva para ADMIN

### Modified Capabilities
- Ninguna. Son endpoints nuevos, no se modifican los existentes.

## Impact

- **Backend**: 4 endpoints nuevos en `Usuario/router.py`, schemas `UsuarioReadWithRoles`, `UsuarioUpdate`, `UsuarioRolesUpdate`, métodos en `service.py` y `repository.py`
- **Frontend**: Nueva página `pages/AdminUsuariosPage.tsx`, ruta `/admin/usuarios` protegida en `App.tsx`
- **API**: Extensión de la API de usuarios, sin cambios breaking
