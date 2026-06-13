"""
Usuario repository module.

Provides database access for Usuario entities with domain-specific
queries: finding users by email, filtering by role, and eager-loading
role relationships.
"""

from sqlmodel import Session, select, col
from sqlalchemy.orm import selectinload

from .models import Usuario
from ..usuario_rol import UsuarioRol
from models.base_repository import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    """
    Repository for Usuario CRUD operations.

    Extends BaseRepository with user-specific queries:
    - get_by_email: find a single user by their unique email.
    - get_all_by_role: paginated user list filtered by role code.
    """

    def __init__(self, session: Session):
        super().__init__(session, Usuario)

    def get_by_email(self, email: str) -> Usuario | None:
        """Find a user by email. Returns None if not found."""
        statement = select(Usuario).where(Usuario.email == email)
        return self.session.exec(statement).first()

    def get_all_by_role(self, rol_codigo: str, skip: int = 0, limit: int = 100):
        """
        Retrieve a paginated list of users filtered by role code.

        Uses an INNER JOIN through the UsuarioRol table to find users
        assigned to the specified role. Eager-loads roles via selectinload
        to prevent N+1 queries when serializing the response.
        """
        statement = (
            select(Usuario)
            .join(UsuarioRol, Usuario.id == UsuarioRol.usuario_id)
            .where(UsuarioRol.rol_codigo == rol_codigo)
        )
        if self._is_soft_delete and not self._incluir_eliminados:
            statement = statement.where(col(Usuario.deleted_at).is_(None))
        statement = (
            statement
            .options(selectinload(Usuario.roles))
            .offset(skip)
            .limit(limit)
            .order_by(Usuario.id.desc())
        )
        return self.session.exec(statement).all()

    def count_by_role(self, rol_codigo: str) -> int:
        """
        Count active (non-deleted) users assigned to a specific role.

        Uses an INNER JOIN through UsuarioRol. Only counts users where
        deleted_at IS NULL (not soft-deleted).
        """
        from sqlmodel import func

        statement = (
            select(func.count(Usuario.id))
            .join(UsuarioRol, Usuario.id == UsuarioRol.usuario_id)
            .where(UsuarioRol.rol_codigo == rol_codigo)
        )
        if self._is_soft_delete:
            from sqlalchemy import column

            statement = statement.where(column("deleted_at").is_(None))
        result = self.session.exec(statement)
        return result.one()

    def count_all(self) -> int:
        """Count all users respecting soft-delete filter."""
        from sqlmodel import func
        statement = select(func.count()).select_from(self.model_class)
        if self._is_soft_delete and not self._incluir_eliminados:
            from sqlalchemy import column
            statement = statement.where(column("deleted_at").is_(None))
        result = self.session.exec(statement)
        return result.one()

    def get_with_roles(self, usuario_id: int):
        """Fetch a user by ID with eager-loaded roles relationship.

        Uses selectinload to prevent N+1 when serializing the response.
        Returns None if the user is not found or has been soft-deleted.
        """
        statement = (
            select(Usuario)
            .where(Usuario.id == usuario_id)
            .options(selectinload(Usuario.roles))
        )
        if self._is_soft_delete and not self._incluir_eliminados:
            from sqlalchemy import column

            statement = statement.where(column("deleted_at").is_(None))
        return self.session.exec(statement).first()
