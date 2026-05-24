from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from models.base import TimestampModel
from ..usuario_rol import UsuarioRol

if TYPE_CHECKING:
    from ..Usuario.models import Usuario


class Rol(TimestampModel, table=True):
    __tablename__ = "rol"

    codigo: str = Field(primary_key=True, max_length=20)  # ← SEMANTIC PK
    nombre: str = Field(unique=True, max_length=50, nullable=False)
    descripcion: Optional[str] = Field(default=None)  # TEXT by default in SQLModel

    usuarios: List["Usuario"] = Relationship(back_populates="roles", link_model=UsuarioRol)
