"""
Categoria service — business logic for category CRUD.

Key rules:
- Category names must be unique (validated before DB insert)
- A parent category must exist when parent_id is provided
- Soft-delete is blocked if active products still reference this category
"""
from typing import List, Optional
from fastapi import HTTPException, status
from sqlmodel import Session
from .models import Categoria
from .repository import CategoriaRepository
from .schemas import CategoriaCreate, CategoriaUpdate
from models.base import get_utc_now
from ..uow import CatalogoDeProductosUnitOfWork


class CategoriaService:
    """Business logic for Category CRUD and validation."""

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100, parent_id: int | None = None) -> List[Categoria]:
        """List categories with optional parent_id filter for subtree navigation.

        Read-only: uses repository directly (no UoW) to avoid commit/expire.
        """
        repo = CategoriaRepository(session)
        return repo.get_all(skip=skip, limit=limit, parent_id=parent_id)

    @staticmethod
    def get_by_id(session: Session, categoria_id: int) -> Optional[Categoria]:
        """Fetch a single non-deleted category.

        Read-only: uses repository directly (no UoW).
        """
        repo = CategoriaRepository(session)
        return repo.get_by_id(categoria_id)

    @staticmethod
    def get_root_categories(session: Session) -> List[Categoria]:
        """Fetch all root categories (no parent) — used to build the category tree.

        Read-only: uses repository directly (no UoW).
        """
        repo = CategoriaRepository(session)
        return repo.get_root_categories()

    @staticmethod
    def create(session: Session, data: CategoriaCreate) -> Categoria:
        """Create a new category.

        Validates:
        - Name uniqueness (no duplicate category names)
        - Parent category exists (FK integrity check)
        """
        repo = CategoriaRepository(session)

        # Validate name uniqueness before attempting DB insert
        if repo.exists_by_nombre(data.nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una categoría con el nombre '{data.nombre}'"
            )

        # Validate parent exists when specified
        if data.parent_id is not None:
            parent = repo.get_parent(data.parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="La categoría padre indicada no existe"
                )

        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_categoria = Categoria(**data.model_dump())
            uow.categorias.add(db_categoria)
            uow.flush()
            uow.categorias.refresh(db_categoria)
            return db_categoria

    @staticmethod
    def update(session: Session, categoria_id: int, data: CategoriaUpdate) -> Optional[Categoria]:
        """Update an existing category. Only provided fields are modified."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_categoria = uow.categorias.get_by_id(categoria_id)
            if not db_categoria:
                return None

            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(db_categoria, key, value)

            uow.categorias.add(db_categoria)
            return db_categoria

    @staticmethod
    def soft_delete(session: Session, categoria_id: int) -> Optional[Categoria]:
        """Soft-delete a category, blocked if active products reference it.

        Business rule: a category with linked active products cannot be
        deleted — the links must be removed first.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_categoria = uow.categorias.get_by_id(categoria_id)
            if not db_categoria:
                return None

            # Check for active product associations before allowing deletion
            if uow.categorias.has_active_products(categoria_id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede eliminar la categoría: tiene productos activos asociados"
                )

            db_categoria.deleted_at = get_utc_now()
            uow.categorias.add(db_categoria)
            return db_categoria
