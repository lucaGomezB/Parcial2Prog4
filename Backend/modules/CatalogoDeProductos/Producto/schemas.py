"""
Producto schemas — Pydantic models for API request/response validation.

These schemas define the shape of data entering (Create, Update) and
leaving (Read) the API for the Product entity.
"""
from typing import Optional, List
from decimal import Decimal
from pydantic import ConfigDict, field_validator
from sqlmodel import SQLModel


class IngredienteAsignado(SQLModel):
    """Payload for assigning an ingredient to a product with metadata."""
    ingrediente_id: int = 0
    cantidad: int = 1
    es_removible: bool = True
    es_principal: bool = False
    orden: int = 0


class CategoriaAsignada(SQLModel):
    """Payload for assigning a category to a product."""
    categoria_id: int
    es_principal: bool = False


class ProductoCreate(SQLModel):
    """Request schema for creating a new product.

    At least one category is required (validated by validar_categorias).
    The optional categoria_principal_id marks one category as primary.
    """
    nombre: str
    descripcion: Optional[str] = None
    receta: Optional[str] = None
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
        """Business rule: a product must belong to at least one category."""
        if not v or len(v) == 0:
            raise ValueError('Se requiere al menos 1 categoría para crear un producto')
        return v


class ProductoUpdate(SQLModel):
    """Request schema for updating an existing product.

    All fields are optional — only provided fields will be applied.
    """
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    receta: Optional[str] = None
    precio_base: Optional[Decimal] = None
    stock_cantidad: Optional[int] = None
    tiempo_prep_min: Optional[int] = None
    disponible: Optional[bool] = None
    categorias_ids: Optional[List[int]] = None


class ProductoRead(SQLModel):
    """Response schema for reading a product.

    tiene_ingredientes is a computed boolean (not a DB column) indicating
    whether the product has any ingredient associations.
    """
    id: int
    nombre: str
    descripcion: Optional[str] = None
    receta: Optional[str] = None
    precio_base: Decimal
    imagenes_url: List[str] = []
    stock_cantidad: int = 0
    tiempo_prep_min: int = 0
    disponible: bool = True
    tiene_ingredientes: bool = False
    model_config = ConfigDict(from_attributes=True)

    @field_validator("imagenes_url", mode="before")
    @classmethod
    def normalize_imagenes_url(cls, v):
        """DB may store NULL in imagenes_url — convert to empty list for type safety."""
        if v is None:
            return []
        return v


class ProductoIngredienteRead(SQLModel):
    """Response schema for an ingredient associated with a product.

    Includes data from the link table (cantidad, es_removible, orden)
    plus the ingredient's name (joined from Ingrediente table).
    """
    ingrediente_id: int
    ingrediente_nombre: str
    cantidad: int
    es_removible: bool
    es_principal: bool
    orden: int
    model_config = ConfigDict(from_attributes=True)


class ProductoCategoriaRead(SQLModel):
    """Response schema for a category associated with a product."""
    categoria_id: int
    categoria_nombre: str
    es_principal: bool
    model_config = ConfigDict(from_attributes=True)
