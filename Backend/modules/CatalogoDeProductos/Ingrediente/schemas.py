from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from .models import IngredienteBase

class IngredienteCreate(IngredienteBase):
    precio_actual: Decimal = 0
    stock_actual: int = 0

class IngredienteUpdate(IngredienteBase):
    nombre: Optional[str] = None
    es_alergeno: Optional[bool] = None
    precio_actual: Optional[Decimal] = None
    stock_actual: Optional[int] = None

class IngredienteRead(BaseModel):
    """Read schema — NO hereda de IngredienteBase ni TimestampModel
    para evitar arrastrar created_at/updated_at que pueden ser NULL en DB."""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_alergeno: bool = False
    precio_actual: Decimal = Decimal('0')
    stock_actual: int = 0
    model_config = ConfigDict(from_attributes=True)

    @field_validator("precio_actual", mode="before")
    @classmethod
    def normalize_precio(cls, v):
        """DB puede tener NULL (nullable=True en migración)."""
        if v is None:
            return Decimal('0')
        return v

class IngredientePrecioUpdate(BaseModel):
    precio: Decimal = Field(ge=0)

class IngredienteStockUpdate(BaseModel):
    stock: int = Field(ge=0)