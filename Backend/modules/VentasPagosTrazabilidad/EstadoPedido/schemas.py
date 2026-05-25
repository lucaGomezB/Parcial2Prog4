from typing import Optional
from pydantic import BaseModel


class EstadoPedidoCreate(BaseModel):
    codigo: str
    descripcion: str
    orden: int
    es_terminal: bool = False


class EstadoPedidoUpdate(BaseModel):
    descripcion: Optional[str] = None
    orden: Optional[int] = None
    es_terminal: Optional[bool] = None


class EstadoPedidoRead(BaseModel):
    codigo: str
    descripcion: str
    orden: int
    es_terminal: bool

    class Config:
        from_attributes = True
