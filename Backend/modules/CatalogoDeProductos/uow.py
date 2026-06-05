"""
Unit of Work for the CatalogoDeProductos module.

Provides a transactional boundary around product, category, and ingredient operations.
All repositories are accessible as attributes (uow.productos, uow.categorias, uow.ingredientes).
"""
from sqlmodel import Session

from .Categoria.repository import CategoriaRepository
from .Ingrediente.repository import IngredienteRepository
from .Producto.repository import ProductoRepository


class CatalogoDeProductosUnitOfWork:
    """Unit of Work for the Catalog module.

    Usage:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            uow.productos.add(...)
            uow.categorias.add(...)
            uow.commit()
    """

    def __init__(self, session: Session):
        self.session = session
        self.productos = ProductoRepository(session)
        self.categorias = CategoriaRepository(session)
        self.ingredientes = IngredienteRepository(session)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        return False

    def add(self, entity):
        """Stage an entity for insert or update."""
        self.session.add(entity)
        return entity

    def flush(self):
        """Send pending SQL to DB without committing (preserves rollback)."""
        self.session.flush()

    def refresh(self, entity):
        """Reload entity from DB after flush to get generated values."""
        self.session.refresh(entity)
        return entity

    def delete(self, entity):
        """Mark an entity for deletion on next flush/commit."""
        self.session.delete(entity)

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
