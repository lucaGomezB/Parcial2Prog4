from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, Relationship
from models.base import TimestampModel, SoftDeleteModel # Ruta absoluta
from ..producto_categoria import ProductoCategoria

if TYPE_CHECKING:
    from ..Producto.models import Producto # Esto evita el círculo en ejecución

class CategoriaBase(TimestampModel):
    nombre: str = Field(index=True, max_length=100)
    descripcion: Optional[str] = None
    parent_id: Optional[int] = Field(default=None, foreign_key="categoria.id") # El parent_id es opcional (las categorías raíz no tienen padre)
    orden_display: int = 0

class Categoria(CategoriaBase, SoftDeleteModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    productos: List["Producto"] = Relationship(back_populates="categorias", link_model=ProductoCategoria) # Se usa "Producto" entre comillas para que SQLModel lo resuelva después
    parent: Optional["Categoria"] = Relationship(back_populates="subcategorias", sa_relationship_kwargs={"remote_side": "Categoria.id"})
    subcategorias: List["Categoria"] = Relationship(back_populates="parent") # Relación hacia los hijos (múltiples subcategorías)
