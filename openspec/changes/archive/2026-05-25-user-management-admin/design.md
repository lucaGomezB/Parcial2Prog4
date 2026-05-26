## Context

El módulo `Usuario` tiene solo `POST /usuarios/`. El `UsuarioRepository` hereda de `BaseRepository[Usuario]` que ya provee `get_all()` paginado con soft-delete filter. El modelo `Usuario` ya hereda de `SoftDeleteModel` (tiene `deleted_at`). La relación M:N con `Rol` existe via `UsuarioRol`. El `require_roles(["ADMIN"])` ya funciona. Solo falta exponer los endpoints y construir el frontend.

## Goals / Non-Goals

**Goals:**
- 4 endpoints backend para gestión de usuarios (list, get, update+roles, soft-delete)
- Página frontend `/admin/usuarios` con listado paginado, filtro por rol, edición y soft-delete
- Todo protegido con `require_roles(["ADMIN"])`

**Non-Goals:**
- No cambiar el modelo de datos existente
- No modificar el endpoint `POST /usuarios/` existente
- No implementar cambio de contraseña (queda para otro change)
- No implementar autogestión de perfil (solo ADMIN gestiona otros usuarios)

## Decisions

1. **Filtro por rol vía query param**: Se agrega `rol_codigo: Optional[str] = Query(None)` a `GET /usuarios/`. Si se provee, filtra usuarios que tengan ese rol (JOIN via UsuarioRol). Si no, retorna todos.

2. **UsuarioRead con roles**: Se crea `UsuarioReadWithRoles` que extiende `UsuarioRead` con una lista de `{codigo, nombre}`. El service usa `selectinload(Usuario.roles)` para eager loading.

3. **PATCH unificado**: Un solo endpoint `PATCH /usuarios/{id}` que acepta tanto campos de usuario como `roles_codigos: list[str]` para re-asignar roles. Si no se envía `roles_codigos`, los roles no se modifican.

4. **Ruta frontend `/admin/usuarios`**: Separada de las rutas normales para dejar claro que es solo ADMIN. No se agrega al navbar general (solo ADMIN puede verlo).

## Risks / Trade-offs

- [Seguridad] El PATCH permite re-asignar roles completamente (no add/remove individual). Es más simple pero menos granular. → Mitigación: es ADMIN-only, se asume uso responsable.
- [Consistencia] Soft-delete de usuario con pedidos activos puede causar orphans. → Mitigación: las FKs tienen `ondelete` configurado, los pedidos quedan pero muestran "Usuario eliminado".
