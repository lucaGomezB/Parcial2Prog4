from typing import Optional
from pydantic import BaseModel


class FormaPagoCreate(BaseModel):
    codigo: str
    descripcion: str
    habilitado: bool = True


class FormaPagoUpdate(BaseModel):
    descripcion: Optional[str] = None
    habilitado: Optional[bool] = None


class FormaPagoRead(BaseModel):
    codigo: str
    descripcion: str
    habilitado: bool

    class Config:
        from_attributes = True
