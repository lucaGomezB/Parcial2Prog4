"""
Categoria schemas — Pydantic models for category API request/response.

Includes a recursive CategoriaTree schema for returning the full
parent-child hierarchy of categories.
"""
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from app.core.base_schema import ReadModel


# --- Input schemas (request validation) ---

class CategoriaCreate(BaseModel):
    """Request schema for creating a new category."""
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: Optional[str] = None
    parent_id: Optional[int] = None
    imagen_url: List[str] = []
    orden_display: int = 0


class CategoriaUpdate(BaseModel):
    """Request schema for updating an existing category. All fields optional."""
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    parent_id: Optional[int] = None
    imagen_url: Optional[List[str]] = None
    orden_display: Optional[int] = None


# --- Output schemas (API response) ---

class CategoriaRead(ReadModel):
    """Response schema for a single category."""
    id: int
    nombre: str
    descripcion: Optional[str] = None
    parent_id: Optional[int] = None
    imagen_url: List[str] = []
    orden_display: int

    @field_validator("imagen_url", mode="before")
    @classmethod
    def normalize_imagen_url(cls, v):
        """DB may store NULL in imagen_url — convert to empty list for type safety."""
        if v is None:
            return []
        return v


class CategoriaTree(CategoriaRead):
    """Response schema for the category hierarchy — includes nested children.

    Used by the /tree endpoint to return the full category tree as nested JSON.
    """
    subcategorias: List["CategoriaTree"] = []


# Forward reference resolution for recursive model
CategoriaTree.model_rebuild()
