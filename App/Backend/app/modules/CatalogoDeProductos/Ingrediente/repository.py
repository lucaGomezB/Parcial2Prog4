"""
Ingrediente repository — data access layer for Ingredient.

Extends BaseRepository with paginated listing and single-fetch
methods for service migration (all queries go through the repo).
"""
from sqlmodel import Session, col, select
from typing import List, Optional

from app.core.base_repository import BaseRepository
from .models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    """Repository for Ingredient with paginated and single-fetch queries."""

    def __init__(self, session: Session):
        super().__init__(session, Ingrediente)

    def get_all_paginated(self, skip: int = 0, limit: int = 100, search: Optional[str] = None):
        """List non-deleted ingredients with pagination and optional text search, newest first."""
        statement = (
            select(Ingrediente)
            .where(col(Ingrediente.deleted_at).is_(None))
        )
        if search:
            statement = statement.where(col(Ingrediente.nombre).ilike(f"%{search}%"))
        statement = statement.offset(skip).limit(limit).order_by(Ingrediente.id.desc())
        return self.session.exec(statement).all()

    def get_by_id(self, ingrediente_id: int) -> Optional[Ingrediente]:
        """Fetch a single non-deleted ingredient by ID."""
        statement = (
            select(Ingrediente)
            .where(Ingrediente.id == ingrediente_id)
            .where(col(Ingrediente.deleted_at).is_(None))
        )
        return self.session.exec(statement).first()

    def count_all(self, search: Optional[str] = None) -> int:
        """Count all non-deleted ingredients, optionally filtered by name search.

        Thin wrapper around BaseRepository.count_all with search_column="nombre".
        """
        return super().count_all(search=search, search_column="nombre" if search else None)
