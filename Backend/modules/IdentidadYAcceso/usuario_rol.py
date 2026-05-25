from datetime import datetime
from typing import Optional
from sqlmodel import Field, UniqueConstraint
from models.base import TimestampModel


class UsuarioRol(TimestampModel, table=True):
    __tablename__ = "usuario_rol"
    __table_args__ = (
        UniqueConstraint("usuario_id", "rol_codigo", name="uq_usuario_rol"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)  # Surrogate PK — needed because rol_codigo can be NULL

    usuario_id: int = Field(
        foreign_key="usuario.id",
        ondelete="CASCADE",    # STRONG: if user deleted, relationship is deleted
        nullable=False
    )
    rol_codigo: Optional[str] = Field(
        default=None,
        foreign_key="rol.codigo",
        ondelete="SET NULL"    # WEAK: if role deleted, relationship stays (codigo becomes NULL)
    )
    asignado_por_id: Optional[int] = Field(
        default=None,
        # NOTE: no FK constraint to avoid ambiguity with usuario_id's FK to usuario.id
    )
    expires_at: Optional[datetime] = Field(default=None)
