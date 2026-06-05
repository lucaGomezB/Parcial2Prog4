"""
Producto models — Product entity for the food catalog.

This module defines the Product SQLModel table and its base mix-in.
Products are the central entity of the catalog: they have a base price,
stock quantity, preparation time, and optional associations with
categories and ingredients.
"""
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import JSON, Column, Field, Numeric, Relationship
from models.base import TimestampModel, SoftDeleteModel
from ..producto_categoria import ProductoCategoria
from ..producto_ingrediente import ProductoIngrediente

if TYPE_CHECKING:
    # String-based forward references avoid circular import at runtime.
    from ..Categoria.models import Categoria
    from ..Ingrediente.models import Ingrediente


class ProductoBase(TimestampModel):
    """Base mix-in with all product fields except the PK and relationships.

    TimestampModel injects created_at / updated_at.
    SoftDeleteModel (used in Producto below) adds deleted_at for logical deletion.
    """
    nombre: str = Field(index=True, max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    receta: Optional[str] = Field(default=None, max_length=5000)
    precio_base: Decimal = Field(default=0, sa_column=Column(Numeric(precision=10, scale=2)))
    precio_actual: Decimal = Field(default=0, sa_column=Column(Numeric(precision=10, scale=2)))
    imagenes_url: List[str] = Field(default=[], sa_column=Column(JSON))  # Stored as JSON array in the database
    stock_cantidad: int = Field(default=0)  # INTEGER CHECK >= 0 DEFAULT 0 — ERD v5
    tiempo_prep_min: int = Field(default=0)
    disponible: bool = Field(default=True)
    es_insumo: bool = Field(default=False)


class Producto(ProductoBase, SoftDeleteModel, table=True):
    """Product table. Maps to 'producto' in the database.

    Relationships:
        - categorias: many-to-many via ProductoCategoria link table
        - ingredientes: many-to-many via ProductoIngrediente link table

    SoftDeleteModel adds deleted_at — rows are never physically deleted.
    """
    __tablename__ = "producto"

    id: Optional[int] = Field(default=None, primary_key=True)
    # String-based relationship names prevent circular import issues at module load time.
    categorias: List["Categoria"] = Relationship(back_populates="productos", link_model=ProductoCategoria)
    ingredientes: List["Ingrediente"] = Relationship(back_populates="productos", link_model=ProductoIngrediente)
