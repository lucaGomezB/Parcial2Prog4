from typing import Optional, List
from pydantic import BaseModel


# --- ESQUEMAS DE ENTRADA (Validación) ---

class CategoriaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    parent_id: Optional[int] = None
    orden_display: int = 0


class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    parent_id: Optional[int] = None
    orden_display: Optional[int] = None


# --- ESQUEMAS DE SALIDA (Respuesta de la API) ---

class CategoriaRead(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    parent_id: Optional[int] = None
    orden_display: int

    class Config:
        from_attributes = True


class CategoriaTree(CategoriaRead):
    """Schema para devolver la jerarquía de categorías con sus hijos."""
    subcategorias: List["CategoriaTree"] = []

    class Config:
        from_attributes = True


CategoriaTree.model_rebuild()