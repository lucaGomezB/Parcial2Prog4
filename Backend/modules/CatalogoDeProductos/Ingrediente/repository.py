"""
Ingrediente repository — data access layer for Ingredient.

Extends BaseRepository with paginated listing and single-fetch
methods for service migration (all queries go through the repo).
"""
from sqlmodel import Session, col, select
from typing import List, Optional

from models.base_repository import BaseRepository
from .models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    """Repository for Ingredient with paginated and single-fetch queries."""

    def __init__(self, session: Session):
        super().__init__(session, Ingrediente)

    def get_all_paginated(self, skip: int = 0, limit: int = 100):
        """List non-deleted ingredients with pagination, newest first."""
        statement = (
            select(Ingrediente)
            .where(col(Ingrediente.deleted_at).is_(None))
            .offset(skip).limit(limit)
            .order_by(Ingrediente.id.desc())
        )
        return self.session.exec(statement).all()

    def get_by_id(self, ingrediente_id: int) -> Optional[Ingrediente]:
        """Fetch a single non-deleted ingredient by ID."""
        statement = (
            select(Ingrediente)
            .where(Ingrediente.id == ingrediente_id)
            .where(col(Ingrediente.deleted_at).is_(None))
        )
        return self.session.exec(statement).first()

    def count_all(self) -> int:
        """Count all non-deleted ingredients."""
        from sqlmodel import func
        from sqlalchemy import column
        statement = select(func.count()).select_from(self.model_class)
        statement = statement.where(column("deleted_at").is_(None))
        result = self.session.exec(statement)
        return result.one()
