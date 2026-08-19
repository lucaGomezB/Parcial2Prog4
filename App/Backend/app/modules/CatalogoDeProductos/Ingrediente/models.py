"""
Ingrediente models — Ingredient entity for product recipes.

Ingredients are the raw materials used to make products. Each ingredient
has its own stock and price, which affects the auto-calculated price
of all products that use it.
"""
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, Numeric
from sqlmodel import Field, Relationship
from app.core.base import TimestampModel, SoftDeleteModel
from ..producto_ingrediente import ProductoIngrediente

# TYPE_CHECKING prevents circular import at runtime
if TYPE_CHECKING:
    from ..Producto.models import Producto
    from ..UnidadMedida.models import UnidadMedida


class IngredienteBase(TimestampModel):
    """Base mix-in with ingredient fields. Used by both model and create schema."""
    nombre: str = Field(unique=True, max_length=100)
    descripcion: Optional[str] = Field(default=None)
    es_alergeno: bool = Field(default=False)
    precio_actual: Decimal = Field(default=0, sa_column=Column(Numeric(10, 2)))
    stock_actual: int = Field(default=0, ge=0)
    unidad_medida_id: Optional[int] = Field(default=None, foreign_key="unidadmedida.id")


class Ingrediente(IngredienteBase, SoftDeleteModel, table=True):
    """Ingredient table with many-to-many relationship to Product.

    When an ingredient's price_actual changes, all products that use
    it get their precio_base recalculated automatically.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    productos: List["Producto"] = Relationship(back_populates="ingredientes", link_model=ProductoIngrediente)
    unidad_medida: Optional["UnidadMedida"] = Relationship()

    @property
    def unidad_medida_simbolo(self) -> Optional[str]:
        """Convenience accessor for unidad_medida.simbolo."""
        if self.unidad_medida:
            return self.unidad_medida.simbolo
        return None
