from typing import Optional
from sqlmodel import SQLModel, Field


class UsuarioRol(SQLModel, table=True):
    __tablename__ = "usuario_rol"

    id: Optional[int] = Field(default=None, primary_key=True)  # Surrogate PK because rol_codigo can be NULL

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
