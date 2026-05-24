from pydantic import BaseModel
from typing import Optional


class RolCreate(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None


class RolUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None


class RolRead(BaseModel):
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
