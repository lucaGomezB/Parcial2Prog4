"""
ProductoCategoria — Many-to-many link table between Product and Category.

Stores whether the category is the primary one (es_principal) for the product.
A product can belong to multiple categories, but typically only one is primary.

Foreign key constraints:
    - producto_id -> producto.id (CASCADE: delete product -> delete link)
    - categoria_id -> categoria.id (RESTRICT: cannot delete referenced category)
"""
from sqlmodel import Field
from app.core.base import TimestampModel


class ProductoCategoria(TimestampModel, table=True):
    """Link table between Producto and Categoria."""
    producto_id: int = Field(foreign_key="producto.id", primary_key=True, ondelete="CASCADE")
    categoria_id: int = Field(foreign_key="categoria.id", primary_key=True, ondelete="RESTRICT")
    es_principal: bool = Field(default=False)
