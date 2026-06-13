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

from typing import List, Optional
from fastapi import HTTPException, status
from sqlmodel import Session

from core.security import get_password_hash
from core.paginated_response import PaginatedResponse

from .models import Usuario
from .repository import UsuarioRepository
from .schemas import UsuarioCreate, UsuarioReadWithRoles, UsuarioUpdateWithRoles
from ..Rol.models import Rol
from ..uow import IdentidadYAccesoUnitOfWork


def crear_usuario(session: Session, datos: UsuarioCreate) -> Usuario:
    """
    Create a new user with hashed password and optional role assignments.

    Flow:
    1. Validate input via Unit of Work transaction.
    2. Create Usuario with bcrypt-hashed password (never plain text).
    3. Flush to get the auto-generated ID.
    4. If roles_codigos provided, look up each Rol and assign via M:N relationship.
    5. Commit the transaction.
    6. Refresh the user and eagerly load roles for the response.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        nuevo_usuario = Usuario(
            nombre=datos.nombre,
            apellido=datos.apellido,
            email=datos.email,
            celular=datos.celular,
            password_hash=get_password_hash(datos.password),
        )
        uow.usuarios.add(nuevo_usuario)
        uow.flush()

        # Assign roles if specified
        if datos.roles_codigos:
            for codigo in datos.roles_codigos:
                rol = uow.roles.get_by_id(codigo)
                if rol:
                    nuevo_usuario.roles.append(rol)

        uow.usuarios.refresh(nuevo_usuario)
        return _load_roles(session, nuevo_usuario)


def _load_roles(session: Session, usuario: Usuario):
    """
    Eager-load the roles relationship after commit.

    Required because after session.commit(), lazy-loaded relationships
    may fail with "lazy loading outside of session". Re-querying with
    get_with_roles ensures roles are available for serialization.
    """
    repo = UsuarioRepository(session)
    repo.get_with_roles(usuario.id)
    return usuario


def listar_usuarios(
    session: Session,
    skip: int = 0,
    limit: int = 100,
    rol_codigo: Optional[str] = None,
    incluir_eliminados: bool = False,
) -> PaginatedResponse[UsuarioReadWithRoles]:
    """
    List users with pagination and optional role filtering.

    When rol_codigo is provided, filters by the UsuarioRol join table.
    Otherwise, returns all non-deleted users ordered by ID descending.
    When incluir_eliminados is True, includes soft-deleted records.
    """
    repo = UsuarioRepository(session)
    if incluir_eliminados:
        repo.with_deleted(True)

    if rol_codigo:
        rows = repo.get_all_by_role(rol_codigo, skip=skip, limit=limit)
    else:
        rows = repo.get_all(skip=skip, limit=limit)

    # Count with the same filters
    count_repo = UsuarioRepository(session)
    if incluir_eliminados:
        count_repo.with_deleted(True)
    if rol_codigo:
        total = count_repo.count_by_role(rol_codigo)
    else:
        total = count_repo.count_all()

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
    repo = UsuarioRepository(session)
    if incluir_eliminados:
        repo.with_deleted(True)
    return repo.get_with_roles(usuario_id)


def actualizar_usuario(
    session: Session,
    usuario_id: int,
    datos: UsuarioUpdateWithRoles,
) -> Optional[Usuario]:
    """
    Partially update a user's fields and/or reassign roles.

    Uses exclude_unset=True to update only the fields sent by the client
    (PATCH semantics). If roles_codigos is provided, the entire role list
    is replaced. If omitted, roles remain unchanged.
    """
    with IdentidadYAccesoUnitOfWork(session) as uow:
        usuario = uow.usuarios.get_by_id(usuario_id)
        if not usuario:
            return None

        # Proteccion: impedir que el unico ADMIN del sistema pierda su rol
        if datos.roles_codigos is not None and "ADMIN" not in datos.roles_codigos:
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
        uow.usuarios.add(usuario)

        # Reassign roles if the field was explicitly provided
        if datos.roles_codigos is not None:
            usuario.roles = []
            for codigo in datos.roles_codigos:
                rol = uow.roles.get_by_id(codigo)
                if rol:
                    usuario.roles.append(rol)

        return _load_roles(session, usuario)


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
        from models.base import get_utc_now
        usuario.deleted_at = get_utc_now()
        uow.usuarios.add(usuario)
        return True
