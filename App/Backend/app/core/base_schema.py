"""
Base schema classes for Pydantic models.

Provides ReadModel — a shared base class for all API response (Read) schemas
that need ORM-to-Pydantic conversion (from_attributes=True).

Usage:
    from app.core.base_schema import ReadModel

    class CategoriaRead(ReadModel):
        id: int
        nombre: str
"""

from pydantic import BaseModel, ConfigDict


class ReadModel(BaseModel):
    """
    Base class for all API Read (response) schemas.

    Automatically enables from_attributes=True via model_config,
    so ORM model instances can be passed directly to Pydantic
    for serialization (e.g., CategoriaRead.model_validate(orm_obj)).

    Subclasses do NOT need to define their own model_config or
    class Config block for from_attributes.
    """

    model_config = ConfigDict(from_attributes=True)
