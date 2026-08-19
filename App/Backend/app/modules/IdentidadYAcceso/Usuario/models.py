"""
Usuario (User) domain model module.

Defines the SQLModel table for usuarios (users) along with its
relationships to roles, refresh tokens, delivery addresses, and orders.

The model uses inheritance from TimestampModel and SoftDeleteModel
for automatic timestamp management and logical deletion support.
"""

from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from ..usuario_rol import UsuarioRol
from ..RefreshToken.models import RefreshToken
from app.core.base import TimestampModel, SoftDeleteModel

# DireccionEntrega imported directly (same-package, no circular risk)
from ..DireccionEntrega.models import DireccionEntrega

if TYPE_CHECKING:
    from ..Rol.models import Rol
    from app.modules.VentasPagosTrazabilidad.Pedido.models import Pedido  # noqa: F401


class UsuarioBase(TimestampModel):
    """
    Base class with shared user fields.

    Inherits created_at and updated_at from TimestampModel.

    Fields:
        nombre: First name (required, max 80 chars).
        apellido: Last name (required, max 80 chars).
        email: Unique email address (UNIQUE constraint, max 254 chars).
        celular: Optional phone number (nullable — not all users have one).
        password_hash: bcrypt hash (60 chars exactly).
    """
    nombre: str = Field(max_length=80, nullable=False)
    apellido: str = Field(max_length=80, nullable=False)
    email: str = Field(unique=True, max_length=254, nullable=False)
    celular: Optional[str] = Field(default=None, max_length=20)
    password_hash: str = Field(max_length=60, nullable=False)


class Usuario(UsuarioBase, SoftDeleteModel, table=True):
    """
    Main user entity — stored in the 'usuario' table.

    Relationships:
    - roles (M:N): Users can have multiple roles via the UsuarioRol join table.
    - refresh_tokens (1:M): Each user has many refresh tokens over time.
    - direcciones_entrega (1:M): Each user can have multiple delivery addresses.
    - pedidos (1:M): Each user can have multiple orders.

    SoftDelete: users are never hard-deleted; deleted_at is set instead.
    This preserves referential integrity for historical orders and addresses.
    """
    __tablename__ = "usuario"
    id: Optional[int] = Field(default=None, primary_key=True)

    # M:N relationship with Rol via UsuarioRol join table
    roles: List["Rol"] = Relationship(back_populates="usuarios", link_model=UsuarioRol)

    # 1:M relationship with RefreshToken
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="usuario")

    # 1:M relationship with DireccionEntrega
    direcciones_entrega: List["DireccionEntrega"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # 1:M relationship with Pedido
    pedidos: List["Pedido"] = Relationship(back_populates="usuario")

# Pedido is NOT imported at runtime to avoid circular imports.
# The Relationship reference uses a string "Pedido" which SQLAlchemy resolves
# lazily during mapper configuration (not at import time). Both Usuario and
# Pedido are imported in main.py before mapper configuration runs, so the
# string reference resolves correctly when needed.
