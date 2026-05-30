from typing import Optional, List
from decimal import Decimal
from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel


class IngredienteAsignado(SQLModel):
    ingrediente_id: int
    cantidad: Decimal = 1
    es_removible: bool = True
    es_principal: bool = False
    orden: int = 0

class CategoriaAsignada(SQLModel):
    categoria_id: int
    es_principal: bool = False


class ProductoCreate(SQLModel):
    nombre: str
    descripcion: Optional[str] = None
    precio_base: Decimal = Decimal('0.00')
    imagenes_url: List[str] = []
    stock_cantidad: int = 0
    tiempo_prep_min: int = 0
    disponible: bool = True
    categorias_ids: List[int] = []
    categoria_principal_id: Optional[int] = None
    ingredientes: Optional[List[IngredienteAsignado]] = []

    @field_validator('categorias_ids')
    @classmethod
    def validar_categorias(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Se requiere al menos 1 categoría para crear un producto')
        return v


class ProductoUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_base: Optional[Decimal] = None
    stock_cantidad: Optional[int] = None
    tiempo_prep_min: Optional[int] = None
    disponible: Optional[bool] = None
    categorias_ids: Optional[List[int]] = None


class ProductoRead(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio_base: Decimal
    imagenes_url: List[str] = []
    stock_cantidad: int = 0
    tiempo_prep_min: int = 0
    disponible: bool = True
    tiene_ingredientes: bool = False
    model_config = ConfigDict(from_attributes=True)

class ProductoIngredienteRead(SQLModel):
    """Schema para devolver un ingrediente asociado a un producto."""
    ingrediente_id: int
    ingrediente_nombre: str
    cantidad: Decimal
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