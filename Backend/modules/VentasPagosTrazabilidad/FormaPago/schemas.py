"""
FormaPago schemas — Pydantic models for payment method API.
"""
from typing import Optional
from pydantic import BaseModel


class FormaPagoCreate(BaseModel):
    """Request schema for creating a new payment method."""
    codigo: str
    descripcion: str
    habilitado: bool = True


class FormaPagoUpdate(BaseModel):
    """Request schema for updating a payment method. All fields optional."""
    descripcion: Optional[str] = None
    habilitado: Optional[bool] = None


class FormaPagoRead(BaseModel):
    """Response schema for a payment method."""
    codigo: str
    descripcion: str
    habilitado: bool

    class Config:
        from_attributes = True
