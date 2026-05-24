from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import JSON, Column, Field, Numeric, Relationship
from models.base import TimestampModel, SoftDeleteModel
from ..producto_categoria import ProductoCategoria
from ..producto_ingrediente import ProductoIngrediente

if TYPE_CHECKING:
    from ..Categoria.models import Categoria
    from ..Ingrediente.models import Ingrediente

class ProductoBase(TimestampModel):
    nombre: str = Field(index=True, max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    precio_base: Decimal = Field(default=0, sa_column=Column(Numeric(precision=10, scale=2))) # Uso de Decimal para precisión financiera (10 dígitos, 2 decimales)
    imagenes_url: List[str] = Field(default=[], sa_column=Column(JSON)) # Almacenamiento como JSON en la base de datos
    tiempo_prep_min: int = Field(default=0)
    disponible: bool = Field(default=True)

class Producto(ProductoBase, SoftDeleteModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Usar strings en los nombres de clases para evitar la carga inmediata y prevenir un bucle infinito facil
    categorias: List["Categoria"] = Relationship(back_populates="productos", link_model=ProductoCategoria)
    ingredientes: List["Ingrediente"] = Relationship(back_populates="productos", link_model=ProductoIngrediente)