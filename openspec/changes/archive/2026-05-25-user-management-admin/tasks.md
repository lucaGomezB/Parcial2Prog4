## 1. Backend — Repository

- [x] 1.1 Agregar método `get_all_by_role(rol_codigo, skip, limit)` en `UsuarioRepository` (JOIN via UsuarioRol)

## 2. Backend — Schemas

- [x] 2.1 Crear `UsuarioReadWithRoles(BaseModel)` con `roles: list[RolRead]`
- [x] 2.2 Crear `UsuarioUpdate(BaseModel)` con campos opcionales: nombre, apellido, email, celular
- [x] 2.3 Crear `UsuarioRolesUpdate(BaseModel)` con `roles_codigos: list[str]`

## 3. Backend — Service

- [x] 3.1 Agregar `listar_usuarios(skip, limit, rol_codigo)` con eager loading de roles
- [x] 3.2 Agregar `obtener_usuario(id)` con eager loading de roles
- [x] 3.3 Agregar `actualizar_usuario(id, data)` que actualiza campos + roles
- [x] 3.4 Agregar `eliminar_usuario(id)` (soft-delete via UoW)

## 4. Backend — Router

- [x] 4.1 Agregar `GET /usuarios/` con paginación y filtro por rol
- [x] 4.2 Agregar `GET /usuarios/{id}` con roles incluidos
- [x] 4.3 Agregar `PATCH /usuarios/{id}` para actualizar datos + roles
- [x] 4.4 Agregar `DELETE /usuarios/{id}` (soft-delete)

## 5. Frontend — API Client

- [x] 5.1 Crear `api/usuarios.ts` con tipos y métodos: `getAll`, `getById`, `update`, `delete`

## 6. Frontend — Admin Page

- [x] 6.1 Crear `pages/AdminUsuariosPage.tsx` con listado paginado + filtro por rol
- [x] 6.2 Agregar modal de edición (datos + roles multi-select)
- [x] 6.3 Agregar botón "Eliminar" con confirmación (soft-delete)
- [x] 6.4 Agregar ruta `/admin/usuarios` en App.tsx protegida solo para ADMIN

## 7. Frontend — Navbar

- [x] 7.1 Agregar link "Usuarios" en navbar solo para ADMIN (dentro de `canSeeFullNav`)
