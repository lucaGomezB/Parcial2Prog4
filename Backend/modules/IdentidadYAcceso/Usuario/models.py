from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from ..usuario_rol import UsuarioRol
from ..RefreshToken.models import RefreshToken

if TYPE_CHECKING:
    from ..Rol.models import Rol


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"

    id: Optional[int] = Field(default=None, primary_key=True)  # BIGSERIAL auto

    nombre: str = Field(max_length=80, nullable=False)
    apellido: str = Field(max_length=80, nullable=False)
    email: str = Field(unique=True, max_length=254, nullable=False)
    celular: Optional[str] = Field(default=None, max_length=20)  # Only nullable field

    password_hash: str = Field(max_length=60, nullable=False)  # bcrypt = exactly 60 chars

    # 1:M relationship with UsuarioRol (roles)
    roles: List["Rol"] = Relationship(back_populates="usuarios", link_model=UsuarioRol)

    # 1:M relationship with RefreshToken
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="usuario")
