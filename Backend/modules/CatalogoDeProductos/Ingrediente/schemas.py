from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from .models import IngredienteBase

class IngredienteCreate(IngredienteBase):
    precio_actual: Decimal = 0
    stock_actual: int = 0

class IngredienteUpdate(IngredienteBase):
    nombre: Optional[str] = None
    es_alergeno: Optional[bool] = None
    precio_actual: Optional[Decimal] = None
    stock_actual: Optional[int] = None

class IngredienteRead(IngredienteBase):
    id: int
    precio_actual: Decimal
    stock_actual: int

class IngredientePrecioUpdate(BaseModel):
    precio: Decimal = Field(ge=0)

class IngredienteStockUpdate(BaseModel):
    stock: int = Field(ge=0)