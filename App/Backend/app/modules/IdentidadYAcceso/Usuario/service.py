"""
Usuario (User) service module.

Implements business logic for user management:
- User creation with optional role assignment (password hashing via core.security).
- User listing with pagination and optional role filtering.
- Single user retrieval with eager-loaded roles.
- Partial update of user fields and/or role reassignment.
- Soft-delete (logical deletion via deleted_at timestamp).

All operations use the IdentidadYAccesoUnitOfWork to ensure
transactional consistency across related entities.
"""

from typing import Optional
from fastapi import HTTPException, status
from sqlmodel import Session

from app.core.security import get_password_hash
from app.core.paginated_response import PaginatedResponse

from .models import Usuario
from .schemas import UsuarioCreate, UsuarioReadWithRoles, UsuarioUpdateWithRoles
from ..usuario_rol import UsuarioRol
from ..uow import IdentidadYAccesoUnitOfWork


def crear_usuario(session: Session, datos: UsuarioCreate, admin_id: int = None) -> Usuario:
    """
    Create a new user with hashed password and optional role assignments.

    Flow:
    1. Validate input via Unit of Work transaction.
    2. Create Usuario with bcrypt-hashed password (never plain text).
    3. Flush to get the auto-generated ID.
    4. If roles_codigos provided, create UsuarioRol links explicitly
       with asignado_por_id set to the admin who created the user.
    5. Commit the transaction.
    6. Refresh the user and eagerly load roles for the response.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        # Check for duplicate email before insert (returns proper 409)
        existing = uow.usuarios.get_by_email(datos.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El email '{datos.email}' ya esta registrado.",
            )

        nuevo_usuario = Usuario(
            nombre=datos.nombre,
            apellido=datos.apellido,
            email=datos.email,
            celular=datos.celular,
            password_hash=get_password_hash(datos.password),
        )
        uow.usuarios.create(nuevo_usuario)
        uow.flush()

        # Assign role if specified (explicit UsuarioRol to set asignado_por_id)
        # A user can only have ONE role
        if datos.roles_codigos:
            rol = uow.roles.get_by_id(datos.roles_codigos)
            if rol:
                enlace = UsuarioRol(
                    usuario_id=nuevo_usuario.id,
                    rol_codigo=datos.roles_codigos,
                    asignado_por_id=admin_id,
                )
                uow.add(enlace)

        uow.usuarios.refresh(nuevo_usuario)
        return uow.usuarios.get_with_roles(nuevo_usuario.id)


def listar_usuarios(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    rol_codigo: Optional[str] = None,
    search: Optional[str] = None,
    incluir_eliminados: bool = False,
) -> PaginatedResponse[UsuarioReadWithRoles]:
    """
    List users with pagination and optional filters (role, text search).

    When search is provided (non-empty), delegates to search_users / count_by_search
    to filter by nombre, apellido, or email (ILIKE). Combines with rol_codigo via AND.
    When search is absent, maintains original behavior (get_all_by_role or get_all).
    When incluir_eliminados is True, includes soft-deleted records.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        if incluir_eliminados:
            uow.usuarios.with_deleted(True)

        if search and search.strip():
            rows = uow.usuarios.search_users(search, rol_codigo=rol_codigo, skip=skip, limit=limit)
            total = uow.usuarios.count_by_search(search, rol_codigo=rol_codigo)
        elif rol_codigo:
            rows = uow.usuarios.get_all_by_role(rol_codigo, skip=skip, limit=limit)
            total = uow.usuarios.count_by_role(rol_codigo)
        else:
            rows = uow.usuarios.get_all(skip=skip, limit=limit)
            total = uow.usuarios.count_all()

        items = [UsuarioReadWithRoles.model_validate(u) for u in rows]
        return PaginatedResponse(
            items=items,
            total=total,
            skip=skip,
            limit=limit,
        )


def obtener_usuario(session: Session, usuario_id: int, incluir_eliminados: bool = False) -> Optional[Usuario]:
    """
    Retrieve a single user by ID with eager-loaded roles.

    Returns None if the user is not found or has been soft-deleted
    (the repository base already filters deleted_at IS NULL).
    When incluir_eliminados is True, includes soft-deleted records.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        if incluir_eliminados:
            uow.usuarios.with_deleted(True)
        return uow.usuarios.get_with_roles(usuario_id)


def actualizar_usuario(
    session: Session,
    usuario_id: int,
    datos: UsuarioUpdateWithRoles,
    admin_id: int = None,
) -> Optional[Usuario]:
    """
    Partially update a user's fields and/or reassign roles.

    Uses exclude_unset=True to update only the fields sent by the client
    (PATCH semantics). If roles_codigos is provided, the entire role list
    is replaced. If omitted, roles remain unchanged.

    When reassigning roles, creates UsuarioRol links explicitly with
    asignado_por_id set to the admin performing the update.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        usuario = uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            return None

        # Proteccion: impedir que el unico ADMIN del sistema pierda su rol
        if datos.roles_codigos is not None and datos.roles_codigos != "ADMIN":
            user_has_admin = any(rol.codigo == "ADMIN" for rol in usuario.roles)
            if user_has_admin:
                admin_count = uow.usuarios.count_by_role("ADMIN")
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No puedes remover el rol ADMIN del unico administrador del sistema",
                    )

        # Update scalar fields only (exclude roles from dict update)
        values = datos.model_dump(exclude_unset=True, exclude={"roles_codigos"})
        for key, value in values.items():
            setattr(usuario, key, value)
        uow.usuarios.update(usuario)

        # Reassign role if the field was explicitly provided
        # (explicit UsuarioRol to set asignado_por_id)
        # A user can only have ONE role
        if datos.roles_codigos is not None:
            # Remove existing role links via repository method
            uow.usuarios.remove_all_roles(usuario.id)
            # Create new UsuarioRol link with asignado_por_id
            rol = uow.roles.get_by_id(datos.roles_codigos)
            if rol:
                enlace = UsuarioRol(
                    usuario_id=usuario.id,
                    rol_codigo=datos.roles_codigos,
                    asignado_por_id=admin_id,
                )
                uow.add(enlace)

        return uow.usuarios.get_with_roles(usuario.id)


def eliminar_usuario(session: Session, usuario_id: int) -> bool:
    """
    Soft-delete a user by setting their deleted_at timestamp.

    The user record is preserved in the database for referential
    integrity (historical orders, addresses, etc.), but filtered out
    by all default queries. Returns False if the user is not found.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        usuario = uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            return False
        from app.core.base import get_utc_now
        usuario.deleted_at = get_utc_now()
        uow.usuarios.update(usuario)
        return True
