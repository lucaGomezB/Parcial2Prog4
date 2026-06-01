"""
UsuarioRol (User-Role join table) module.

Defines the many-to-many relationship between usuarios (users) and
roles. This intermediate table enables flexible role assignments with
additional metadata (who assigned the role, optional expiration).

Key design decisions:
- Surrogate PK (auto-increment id) instead of composite PK because
  rol_codigo can be NULL (SET NULL on role deletion).
- UniqueConstraint on (usuario_id, rol_codigo) prevents duplicate assignments.
- ondelete=CASCADE on usuario_id: removing a user removes their role links.
- ondelete=SET NULL on rol_codigo: removing a role preserves the link
  for audit purposes (rol_codigo becomes NULL).
"""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, UniqueConstraint
from models.base import TimestampModel


class UsuarioRol(TimestampModel, table=True):
    """
    Many-to-many join table between Usuario and Rol.

    Tracks which roles are assigned to which users, including metadata
    about who made the assignment and whether it has an expiration date.

    Table: usuario_rol
    Constraints:
    - uq_usuario_rol: unique per (usuario_id, rol_codigo) pair.
    """
    __tablename__ = "usuario_rol"
    __table_args__ = (
        UniqueConstraint("usuario_id", "rol_codigo", name="uq_usuario_rol"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    usuario_id: int = Field(
        foreign_key="usuario.id",
        ondelete="CASCADE",      # Strong: delete role links when user is deleted
        nullable=False
    )
    rol_codigo: Optional[str] = Field(
        default=None,
        foreign_key="rol.codigo",
        ondelete="SET NULL"      # Weak: keep link if role is deleted (audit trail)
    )
    asignado_por_id: Optional[int] = Field(
        default=None,
        # No FK constraint — avoids ambiguity with usuario_id's FK to the same table
    )
    expires_at: Optional[datetime] = Field(default=None)
