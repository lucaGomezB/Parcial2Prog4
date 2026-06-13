"""
Categoria repository — data access layer for Category.

Extends BaseRepository with queries for root categories (no parent),
optional parent_id filtering, uniqueness checks, and product-link validation.
"""
from sqlmodel import Session, col, select
from typing import Optional

from models.base_repository import BaseRepository
from .models import Categoria


class CategoriaRepository(BaseRepository[Categoria]):
    """Repository for Category with hierarchy-aware queries."""

    def __init__(self, session: Session):
        super().__init__(session, Categoria)

    def get_root_categories(self):
        """Return all root categories (parent_id IS NULL) that are not soft-deleted."""
        statement = select(Categoria).where(col(Categoria.parent_id).is_(None), col(Categoria.deleted_at).is_(None))
        return self.session.exec(statement).all()

    def get_by_id(self, categoria_id: int) -> Optional[Categoria]:
        """Fetch a single non-deleted category by its ID."""
        statement = select(Categoria).where(Categoria.id == categoria_id, col(Categoria.deleted_at).is_(None))
        return self.session.exec(statement).first()

    def get_all(self, skip: int = 0, limit: int = 100, parent_id: int | None = None):
        """List non-deleted categories with optional parent_id filter, newest first."""
        statement = select(Categoria).where(col(Categoria.deleted_at).is_(None))
        if parent_id is not None:
            statement = statement.where(Categoria.parent_id == parent_id)
        statement = statement.offset(skip).limit(limit).order_by(Categoria.id.desc())
        return self.session.exec(statement).all()

    def exists_by_nombre(self, nombre: str) -> bool:
        """Check if a non-deleted category with the given name already exists."""
        statement = select(Categoria).where(Categoria.nombre == nombre, col(Categoria.deleted_at).is_(None))
        return self.session.exec(statement).first() is not None

    def get_parent(self, parent_id: int) -> Optional[Categoria]:
        """Fetch a parent category by ID (alias for get_by_id with explicit name)."""
        return self.get_by_id(parent_id)

    def has_active_products(self, categoria_id: int) -> bool:
        """Check whether any active (non-deleted) product references this category."""
        from ..producto_categoria import ProductoCategoria
        from ..Producto.models import Producto

        statement = (
            select(ProductoCategoria)
            .join(Producto, ProductoCategoria.producto_id == Producto.id)
            .where(
                ProductoCategoria.categoria_id == categoria_id,
                col(Producto.deleted_at).is_(None),
            )
            .limit(1)
        )
        return self.session.exec(statement).first() is not None

    def count_all(self) -> int:
        """Count all non-deleted categories."""
        from sqlmodel import func
        from sqlalchemy import column
        statement = select(func.count()).select_from(self.model_class)
        statement = statement.where(column("deleted_at").is_(None))
        result = self.session.exec(statement)
        return result.one()
