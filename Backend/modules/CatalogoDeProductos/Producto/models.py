from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import JSON, Column, Field, Numeric, Relationship
from models.base import TimestampModel, SoftDeleteModel
from ..producto_categoria import ProductoCategoria
from ..producto_ingrediente import ProductoIngrediente

if TYPE_CHECKING:
    from ..Categoria.models import Categoria
    from ..Ingrediente.models import Ingrediente

class ProductoMedida(TimestampModel, table=True):
    __tablename__ = "productomedida"

    id: Optional[int] = Field(default=None, primary_key=True)
    producto_id: int = Field(foreign_key="producto.id", nullable=False)
    nombre: str = Field(max_length=100, nullable=False)
    precio: Decimal = Field(sa_column=Column(Numeric(precision=10, scale=2), nullable=False))
    stock: int = Field(default=0)
    orden: int = Field(default=0)
    disponible: bool = Field(default=True)

    # Relationship
    producto: "Producto" = Relationship(back_populates="medidas")


class ProductoBase(TimestampModel):
    nombre: str = Field(index=True, max_length=150)
    descripcion: Optional[str] = Field(default=None, max_length=500)
    precio_base: Decimal = Field(default=0, sa_column=Column(Numeric(precision=10, scale=2))) # Uso de Decimal para precisión financiera (10 dígitos, 2 decimales)
    imagenes_url: List[str] = Field(default=[], sa_column=Column(JSON)) # Almacenamiento como JSON en la base de datos
    stock_cantidad: int = Field(default=0) # INTEGER CHECK >= 0 DEFAULT 0 — ERD v5
    tiempo_prep_min: int = Field(default=0)
    disponible: bool = Field(default=True)

class Producto(ProductoBase, SoftDeleteModel, table=True):
    __tablename__ = "producto"

    id: Optional[int] = Field(default=None, primary_key=True)
    # Usar strings en los nombres de clases para evitar la carga inmediata y prevenir un bucle infinito facil
    categorias: List["Categoria"] = Relationship(back_populates="productos", link_model=ProductoCategoria)
    ingredientes: List["Ingrediente"] = Relationship(back_populates="productos", link_model=ProductoIngrediente)
    medidas: List["ProductoMedida"] = Relationship(back_populates="producto", sa_relationship_kwargs={"cascade": "all, delete-orphan"})