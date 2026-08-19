"""
UnidadMedida schemas — Pydantic models for API request/response validation.

Design decisions:
    - tipo uses Literal validation (application-level, not DB enum — D3)
    - UnidadMedidaRead includes all 6 fields (id, nombre, simbolo, tipo, factor_conversion, created_at)
    - No updated_at (immutable catalog — D4)
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
from sqlmodel import SQLModel, Field
from app.core.base_schema import ReadModel

# Allowed measurement unit types
UnidadMedidaTipo = Literal["masa", "volumen", "unidad", "area"]


class UnidadMedidaBase(SQLModel):
    """Shared fields for create/update/read."""
    nombre: str = Field(max_length=50)
    simbolo: str = Field(max_length=10)
    tipo: UnidadMedidaTipo


class UnidadMedidaCreate(UnidadMedidaBase):
    """Request schema for creating a new measurement unit.

    All three fields are required: nombre, simbolo, and tipo.
    tipo is validated against the Literal set (masa, volumen, unidad, area).
    factor_conversion defaults to 1 and must be > 0.
    """
    factor_conversion: Decimal = Field(default=Decimal("1"), gt=0, decimal_places=3)


class UnidadMedidaUpdate(SQLModel):
    """Request schema for updating a measurement unit.

    All fields are optional — only provided fields will be updated.
    """
    nombre: Optional[str] = None
    simbolo: Optional[str] = None
    tipo: Optional[UnidadMedidaTipo] = None
    factor_conversion: Optional[Decimal] = Field(default=None, gt=0, decimal_places=3)


class UnidadMedidaRead(ReadModel, UnidadMedidaBase):
    """Response schema for reading a measurement unit.

    Includes all columns: id, nombre, simbolo, tipo, factor_conversion, created_at.
    """
    id: int
    factor_conversion: Decimal
    created_at: datetime
