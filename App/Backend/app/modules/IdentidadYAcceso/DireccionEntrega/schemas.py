"""
Pydantic schemas for DireccionEntrega (Delivery Address) endpoints.

Defines request and response models for creating, updating, and
reading delivery addresses.
"""

from decimal import Decimal
from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.core.base_schema import ReadModel


class DireccionEntregaCreate(BaseModel):
    """Request schema for creating a new delivery address."""
    alias: Optional[str] = None
    linea1: str
    linea2: Optional[str] = None
    ciudad: str
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: bool = False
    es_local: bool = False


class DireccionEntregaUpdate(BaseModel):
    """Request schema for updating a delivery address. All fields optional (PATCH)."""
    alias: Optional[str] = None
    linea1: Optional[str] = None
    linea2: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: Optional[bool] = None
    es_local: Optional[bool] = None


class DireccionEntregaRead(ReadModel):
    """Response schema for delivery address data."""
    id: int
    usuario_id: int
    alias: Optional[str] = None
    linea1: str
    linea2: Optional[str] = None
    ciudad: str
    provincia: Optional[str] = None
    codigo_postal: Optional[str] = None
    latitud: Optional[Decimal] = None
    longitud: Optional[Decimal] = None
    es_principal: bool
    es_local: bool = False
    created_at: datetime
    updated_at: datetime
