"""
Ingrediente schemas — Pydantic models for ingredient API request/response.

IngredienteRead deliberately avoids inheriting TimestampModel fields
to prevent serialization issues when those columns are NULL in the DB.
"""
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.core.base_schema import ReadModel
from .models import IngredienteBase


class IngredienteCreate(IngredienteBase):
    """Request schema for creating an ingredient."""
    precio_actual: Decimal = 0
    stock_actual: int = 0
    unidad_medida_id: int  # mandatory — ingredient must have a unit of measure

    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError('El nombre no puede estar vacio')
        return stripped


class IngredienteUpdate(IngredienteBase):
    """Request schema for updating an ingredient. All fields optional."""
    nombre: Optional[str] = None
    es_alergeno: Optional[bool] = None
    precio_actual: Optional[Decimal] = None
    stock_actual: Optional[int] = None

    @field_validator('nombre')
    @classmethod
    def validate_nombre(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v  # Allow None for Update (optional field)
        stripped = v.strip()
        if not stripped:
            raise ValueError('El nombre no puede estar vacio')
        return stripped


class IngredienteRead(ReadModel):
    """Response schema for reading an ingredient.

    NOT inheriting from IngredienteBase or TimestampModel to avoid
    dragging created_at/updated_at which may be NULL in the DB.
    """
    id: int
    nombre: str
    descripcion: Optional[str] = None
    es_alergeno: bool = False
    precio_actual: Decimal = Decimal('0')
    stock_actual: int = 0
    unidad_medida_id: Optional[int] = None
    unidad_medida_simbolo: Optional[str] = None

    @field_validator("precio_actual", mode="before")
    @classmethod
    def normalize_precio(cls, v):
        """DB may have NULL (nullable=True in migration) — default to 0."""
        if v is None:
            return Decimal('0')
        return v


class IngredientePrecioUpdate(BaseModel):
    """Request schema for updating only the ingredient price."""
    precio: Decimal = Field(ge=0)


class IngredienteStockUpdate(BaseModel):
    """Request schema for updating only the ingredient stock."""
    stock: int = Field(ge=0)


class AfectadoProductoRead(BaseModel):
    """Response schema for a product affected by an ingredient's stock.
    Includes derived stock computed from ingredient availability and
    manual stock for es_producto_terminado products."""
    id: int
    nombre: str
    stock_derivado: int
    es_producto_terminado: bool = False
    stock_manual: Optional[int] = None
