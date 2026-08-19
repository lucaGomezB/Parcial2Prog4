"""
ProductoIngrediente — Many-to-many link table between Product and Ingredient.

Stores relationship metadata:
    - es_removible: whether the customer can remove this ingredient from the product
    - es_principal: whether this is the main/primary ingredient
    - orden: display order within the product
    - cantidad: how much of this ingredient is needed per product unit (Decimal)
    - unidad_medida_id: optional FK to UnidadMedida for the ingredient's unit

Foreign key constraints:
    - producto_id -> producto.id (CASCADE: delete product -> delete link)
    - ingrediente_id -> ingrediente.id (RESTRICT: cannot delete referenced ingredient)
    - unidad_medida_id -> unidadmedida.id (optional, SET NULL on delete)
"""

from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlmodel import Column, Field, Numeric, Relationship
from app.core.base import TimestampModel

if TYPE_CHECKING:
    from ..UnidadMedida.models import UnidadMedida


class ProductoIngrediente(TimestampModel, table=True):
    """Link table between Producto and Ingrediente with relationship metadata."""
    producto_id: int = Field(foreign_key="producto.id", primary_key=True, ondelete="CASCADE")
    ingrediente_id: int = Field(foreign_key="ingrediente.id", primary_key=True, ondelete="RESTRICT")
    es_removible: bool = Field(default=False)
    es_principal: bool = Field(default=False)
    orden: int = Field(default=0)
    cantidad: Decimal = Field(
        default=Decimal("1"),
        sa_column=Column(Numeric(10, 3), nullable=False),
    )
    unidad_medida_id: Optional[int] = Field(default=None, foreign_key="unidadmedida.id")
    unidad_medida: Optional["UnidadMedida"] = Relationship(back_populates="producto_ingredientes")
