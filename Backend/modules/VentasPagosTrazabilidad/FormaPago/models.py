from typing import Optional
from sqlmodel import Field
from models.base import TimestampModel


class FormaPago(TimestampModel, table=True):
    __tablename__ = "formapago"

    codigo: str = Field(primary_key=True, max_length=20)
    descripcion: str = Field(max_length=80, nullable=False)
    habilitado: bool = Field(default=True, nullable=False)
