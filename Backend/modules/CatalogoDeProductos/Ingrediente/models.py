from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, Relationship
from models.base import TimestampModel, SoftDeleteModel
from ..producto_ingrediente import ProductoIngrediente

# Esto evita el círculo en tiempo de ejecución
if TYPE_CHECKING:
    from ..Producto.models import Producto

class IngredienteBase(TimestampModel):
    nombre: str = Field(index=True, max_length=100)
    es_alergeno: bool = Field(default=True) #Tiene que ser True para no herir a alguien accidentalmente si se cargó mal inicialmente.

class Ingrediente(IngredienteBase, SoftDeleteModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    productos: List["Producto"] = Relationship(back_populates="ingredientes", link_model=ProductoIngrediente)