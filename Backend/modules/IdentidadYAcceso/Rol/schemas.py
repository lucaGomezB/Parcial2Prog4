"""
Pydantic schemas for Rol (Role) endpoints.

Defines request and response models for role CRUD operations.
"""
from pydantic import BaseModel
from typing import Optional


class RolCreate(BaseModel):
    """Request schema for creating a new role. Requires codigo and nombre."""
    codigo: str
    nombre: str
    descripcion: Optional[str] = None


class RolUpdate(BaseModel):
    """Request schema for updating a role. All fields optional (PATCH semantics)."""
    nombre: Optional[str] = None
    descripcion: Optional[str] = None


class RolRead(BaseModel):
    """Response schema for role data. Excludes timestamps."""
    codigo: str
    nombre: str
    descripcion: Optional[str] = None
