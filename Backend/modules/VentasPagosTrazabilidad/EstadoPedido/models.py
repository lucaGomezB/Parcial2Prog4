from typing import Optional
from sqlmodel import Field
from models.base import TimestampModel


class EstadoPedido(TimestampModel, table=True):
    __tablename__ = "estadopedido"

    codigo: str = Field(primary_key=True, max_length=20)
    descripcion: str = Field(max_length=80, nullable=False)
    orden: int = Field(nullable=False)
    es_terminal: bool = Field(nullable=False)
