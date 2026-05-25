from decimal import Decimal
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DireccionEntregaCreate(BaseModel):
    alias: Optional[str] = None
    linea1: str
    linea2: Optional[str] = None
    ciudad: str
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: bool = False


class DireccionEntregaUpdate(BaseModel):
    alias: Optional[str] = None
    linea1: Optional[str] = None
    linea2: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None


class DireccionEntregaRead(BaseModel):
    id: int
    usuario_id: int
    alias: Optional[str] = None
    linea1: str
    linea2: Optional[str] = None
    ciudad: str
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
