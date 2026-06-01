"""
Ingrediente repository — data access layer for Ingredient.

Standard CRUD only — no custom query methods needed beyond BaseRepository.
"""
from sqlmodel import Session

from models.base_repository import BaseRepository
from .models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    """Repository for Ingredient. Inherits standard CRUD from BaseRepository."""

    def __init__(self, session: Session):
        super().__init__(session, Ingrediente)
