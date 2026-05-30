from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, Numeric
from sqlmodel import Field, Relationship
from models.base import TimestampModel, SoftDeleteModel
from ..producto_ingrediente import ProductoIngrediente

# Esto evita el círculo en tiempo de ejecución
if TYPE_CHECKING:
    from ..Producto.models import Producto

class IngredienteBase(TimestampModel):
    nombre: str = Field(unique=True, max_length=100)
    descripcion: Optional[str] = Field(default=None)
    es_alergeno: bool = Field(default=False)
    precio_actual: Decimal = Field(default=0, sa_column=Column(Numeric(10,2)))
    stock_actual: int = Field(default=0, ge=0)

class Ingrediente(IngredienteBase, SoftDeleteModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    productos: List["Producto"] = Relationship(back_populates="ingredientes", link_model=ProductoIngrediente)