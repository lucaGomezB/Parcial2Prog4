"""
Categoria models — Category entity for product classification.

Categories form a hierarchy via the self-referencing parent_id field.
Root categories have parent_id = NULL. The category tree is used for
navigation and filtering in the frontend.
"""
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, Relationship
from models.base import TimestampModel, SoftDeleteModel
from ..producto_categoria import ProductoCategoria

if TYPE_CHECKING:
    from ..Producto.models import Producto  # Avoids circular import at runtime


class CategoriaBase(TimestampModel):
    """Base mix-in with all category fields except the PK and relationships."""
    nombre: str = Field(unique=True, max_length=100)
    descripcion: Optional[str] = None
    parent_id: Optional[int] = Field(default=None, foreign_key="categoria.id")  # NULL for root categories
    imagen_url: Optional[str] = Field(default=None)
    orden_display: int = 0


class Categoria(CategoriaBase, SoftDeleteModel, table=True):
    """Category table with self-referencing parent-child hierarchy.

    - parent: the parent category (NULL for root categories)
    - subcategorias: all child categories under this one
    - productos: many-to-many via ProductoCategoria link table

    Soft deletion is used — rows are never physically removed from the DB.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    productos: List["Producto"] = Relationship(back_populates="categorias", link_model=ProductoCategoria)
    parent: Optional["Categoria"] = Relationship(
        back_populates="subcategorias",
        sa_relationship_kwargs={"remote_side": "Categoria.id"}
    )
    subcategorias: List["Categoria"] = Relationship(back_populates="parent")
