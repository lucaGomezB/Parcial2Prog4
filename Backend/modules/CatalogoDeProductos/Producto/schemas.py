from typing import Optional, List
from decimal import Decimal
from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel
from .models import ProductoBase

class IngredienteAsignado(SQLModel):
    ingrediente_id: int
    es_removible: bool = True
    es_principal: bool = False
    orden: int = 0

class CategoriaAsignada(SQLModel):
    categoria_id: int
    es_principal: bool = False


class ProductoCreate(ProductoBase):
    categorias_ids: List[int] = []
    categoria_principal_id: Optional[int] = None
    ingredientes: Optional[List[IngredienteAsignado]] = []

    @field_validator('categorias_ids')
    @classmethod
    def validar_categorias(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Se requiere al menos 1 categoría para crear un producto')
        return v

    @field_validator('ingredientes')
    @classmethod
    def validar_ingredientes(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Se requiere al menos 1 ingrediente para crear un producto')
        return v

class ProductoUpdate(ProductoBase):
    nombre: Optional[str] = None
    precio_base: Optional[Decimal] = None
    disponible: Optional[bool] = None
    categorias_ids: Optional[List[int]] = None

class ProductoRead(ProductoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ProductoIngredienteRead(SQLModel):
    """Schema para devolver un ingrediente asociado a un producto."""
    ingrediente_id: int
    ingrediente_nombre: str
    es_removible: bool
    es_principal: bool
    orden: int
    model_config = ConfigDict(from_attributes=True)

class ProductoCategoriaRead(SQLModel):
    """Schema para devolver una categoría asociada a un producto."""
    categoria_id: int
    categoria_nombre: str
    es_principal: bool
    model_config = ConfigDict(from_attributes=True)