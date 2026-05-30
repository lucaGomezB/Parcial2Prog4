from decimal import Decimal
from sqlalchemy import Column, Numeric
from sqlmodel import Field
from models.base import TimestampModel

class ProductoIngrediente(TimestampModel, table=True):
    producto_id: int = Field(foreign_key="producto.id", primary_key=True, ondelete="CASCADE") # Si se elimina el producto, se elimina esta fila de la tabla intermedia
    ingrediente_id: int = Field(foreign_key="ingrediente.id", primary_key=True, ondelete="RESTRICT") # Si se elimina el ingrediente, la relación se rompe pero el producto sigue existiendo
    es_removible: bool = Field(default=False)
    es_principal: bool = Field(default=False)
    orden: int = Field(default=0)
    cantidad: Decimal = Field(default=1, sa_column=Column(Numeric(10,2)))