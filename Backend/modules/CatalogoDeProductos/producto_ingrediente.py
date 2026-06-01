"""
ProductoIngrediente — Many-to-many link table between Product and Ingredient.

Stores relationship metadata:
    - es_removible: whether the customer can remove this ingredient from the product
    - es_principal: whether this is the main/primary ingredient
    - orden: display order within the product
    - cantidad: how much of this ingredient is needed per product unit

Foreign key constraints:
    - producto_id -> producto.id (CASCADE: delete product -> delete link)
    - ingrediente_id -> ingrediente.id (RESTRICT: cannot delete referenced ingredient)
"""
from sqlmodel import Field
from models.base import TimestampModel


class ProductoIngrediente(TimestampModel, table=True):
    """Link table between Producto and Ingrediente with relationship metadata."""
    producto_id: int = Field(foreign_key="producto.id", primary_key=True, ondelete="CASCADE")
    ingrediente_id: int = Field(foreign_key="ingrediente.id", primary_key=True, ondelete="RESTRICT")
    es_removible: bool = Field(default=False)
    es_principal: bool = Field(default=False)
    orden: int = Field(default=0)
    cantidad: int = Field(default=1)
