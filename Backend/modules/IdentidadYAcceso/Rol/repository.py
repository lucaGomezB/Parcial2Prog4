"""
Rol (Role) repository module.

Provides database access for Rol entities. Adds a domain-specific
lookup method (get_by_codigo) since the Rol model uses a semantic
primary key instead of the conventional 'id' field.
"""

from sqlmodel import Session

from .models import Rol
from models.base_repository import BaseRepository


class RolRepository(BaseRepository[Rol]):
    """
    Repository for Rol CRUD operations.

    Extends BaseRepository with a get_by_codigo helper that uses
    session.get() with the semantic PK directly.
    """

    def __init__(self, session: Session):
        super().__init__(session, Rol)

    def get_by_codigo(self, codigo: str) -> Rol | None:
        """Find a role by its semantic code (primary key)."""
        return self.session.get(Rol, codigo)
