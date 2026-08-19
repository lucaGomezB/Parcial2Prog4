"""
Rol (Role) domain model module.

Defines the SQLModel table for roles used in Role-Based Access Control (RBAC).

The Rol model uses a SEMANTIC primary key (codigo) instead of an
auto-incremented integer. This is appropriate because roles are a
small, relatively static set with meaningful business identifiers
(ADMIN, CLIENT, STOCK, etc.).
"""

from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from app.core.base import TimestampModel
from ..usuario_rol import UsuarioRol

if TYPE_CHECKING:
    from ..Usuario.models import Usuario


class Rol(TimestampModel, table=True):
    """
    System role entity — stored in the 'rol' table.

    Primary key is a semantic string code (e.g., 'ADMIN', 'CLIENT')
    rather than an auto-generated integer. This makes foreign key
    references readable in the database.

    Relationships:
    - usuarios (M:N): A role can be assigned to many users via UsuarioRol.

    TimestampModel inheritance: adds created_at and updated_at fields.
    """
    __tablename__ = "rol"

    codigo: str = Field(primary_key=True, max_length=20)  # Semantic PK: e.g., "ADMIN", "CLIENT"
    nombre: str = Field(unique=True, max_length=50, nullable=False)
    descripcion: Optional[str] = Field(default=None)

    usuarios: List["Usuario"] = Relationship(back_populates="roles", link_model=UsuarioRol)
