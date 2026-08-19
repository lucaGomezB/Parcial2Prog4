"""
Producto models

This module defines the Product SQLModel table and its base mix-in.
Products are the central entity of the catalog: they have a base price,
stock quantity, preparation time, and optional associations with
categories and ingredients.
"""

from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import JSON, Column, Field, Numeric, Relationship
from app.core.base import TimestampModel, SoftDeleteModel
from ..producto_categoria import ProductoCategoria
from ..producto_ingrediente import ProductoIngrediente

if TYPE_CHECKING:
    # String-based forward references avoid circular import at runtime.
    from ..Categoria.models import Categoria
    from ..Ingrediente.models import Ingrediente
    from ..UnidadMedida.models import UnidadMedida


class ProductoBase(TimestampModel):
    """Base mix-in with all product fields except the PK and relationships."""
    nombre: str = Field(index=True, max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    receta: Optional[str] = Field(default=None, max_length=5000)
    precio_base: Decimal = Field(default=0, sa_column=Column(Numeric(precision=10, scale=2)))
    precio_actual: Decimal = Field(default=0, sa_column=Column(Numeric(precision=10, scale=2)))
    imagenes_url: List[str] = Field(default=[], sa_column=Column(JSON))  # Stored as JSON array in the database
    stock_cantidad: int = Field(default=0, ge=0)  # INTEGER CHECK >= 0 DEFAULT 0 — ERD v5
    stock_manual: Optional[int] = Field(default=None, nullable=True)  # Phase 1: manual stock for finished products (es_producto_terminado=True)
    tiempo_prep_min: int = Field(default=0)
    disponible: bool = Field(default=True)
    es_producto_terminado: bool = Field(default=False)
    unidad_medida_id: Optional[int] = Field(default=None, foreign_key="unidadmedida.id")


class Producto(ProductoBase, SoftDeleteModel, table=True):
    """Product table. Maps to 'producto' in the database.

    Relaciones:
        - categorias: many-to-many via ProductoCategoria link table
        - ingredientes: many-to-many via ProductoIngrediente link table
        - unidad_medida: optional FK to UnidadMedida

    SoftDeleteModel adds deleted_at — rows are never physically deleted.
    """
    __tablename__ = "producto"

    id: Optional[int] = Field(default=None, primary_key=True)
    # String-based relationship names prevent circular import issues at module load time.
    categorias: List["Categoria"] = Relationship(back_populates="productos", link_model=ProductoCategoria)
    ingredientes: List["Ingrediente"] = Relationship(back_populates="productos", link_model=ProductoIngrediente)
    unidad_medida: Optional["UnidadMedida"] = Relationship(back_populates="productos")

    @property
    def unidad_medida_simbolo(self) -> Optional[str]:
        """Convenience accessor for unidad_medida.simbolo. Returns None when unidad_medida is not set or not loaded.
        """
        if self.unidad_medida:
            return self.unidad_medida.simbolo
        return None
