from typing import List, Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from ..usuario_rol import UsuarioRol
from ..RefreshToken.models import RefreshToken
from models.base import TimestampModel, SoftDeleteModel

# Direct imports — no circular dependency because these modules use
# TYPE_CHECKING for their back-references to Usuario.
from ..DireccionEntrega.models import DireccionEntrega
from modules.VentasPagosTrazabilidad.Pedido.models import Pedido

if TYPE_CHECKING:
    from ..Rol.models import Rol


class UsuarioBase(TimestampModel):
    nombre: str = Field(max_length=80, nullable=False)
    apellido: str = Field(max_length=80, nullable=False)
    email: str = Field(unique=True, max_length=254, nullable=False)
    celular: Optional[str] = Field(default=None, max_length=20)  # Only nullable field
    password_hash: str = Field(max_length=60, nullable=False)  # bcrypt = exactly 60 chars

class Usuario(UsuarioBase, SoftDeleteModel, table=True):
    __tablename__ = "usuario"
    id: Optional[int] = Field(default=None, primary_key=True)  # BIGSERIAL auto

    # M:N relationship with Rol via UsuarioRol
    roles: List["Rol"] = Relationship(back_populates="usuarios", link_model=UsuarioRol)

    # 1:M relationship with RefreshToken
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="usuario")

    # 1:M relationship with DireccionEntrega
    direcciones_entrega: List["DireccionEntrega"] = Relationship(back_populates="usuario", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    # 1:M relationship with Pedido
    pedidos: List["Pedido"] = Relationship(back_populates="usuario")
