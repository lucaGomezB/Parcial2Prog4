from sqlmodel import Field
from models.base import TimestampModel

class ProductoCategoria(TimestampModel, table=True):
    producto_id: int = Field(foreign_key="producto.id", primary_key=True, ondelete="CASCADE") # Al añadir ondelete="CASCADE", si se borra el producto. La fila de esta tabla automáticamente deja de existir
    categoria_id: int = Field(foreign_key="categoria.id", primary_key=True, ondelete="RESTRICT")
    es_principal: bool = Field(default=False)