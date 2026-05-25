from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship
from sqlalchemy import Numeric
from models.base import TimestampModel, SoftDeleteModel

if TYPE_CHECKING:
    from ..Usuario.models import Usuario


class DireccionEntregaBase(TimestampModel):
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str = Field(max_length=100, nullable=False)
    linea2: Optional[str] = Field(max_length=100)
    ciudad: str = Field(max_length=100, nullable=False)
    provincia: Optional[str] = Field(max_length=100)
    codigo_postal: Optional[str] = Field(max_length=10)
    latitud: Optional[Decimal] = Field(default=None, sa_type=Numeric(precision=9, scale=6))
    longitud: Optional[Decimal] = Field(default=None, sa_type=Numeric(precision=9, scale=6))
    es_principal: bool = Field(default=False)


class DireccionEntrega(DireccionEntregaBase, SoftDeleteModel, table=True):
    __tablename__: str = "direcciones_entrega"
    id: Optional[int] = Field(default=None, primary_key=True)

    # N:1 Relationship to Usuario
    usuario_id: int = Field(foreign_key="usuario.id", nullable=False, ondelete="CASCADE")
    usuario: "Usuario" = Relationship(back_populates="direcciones_entrega")
