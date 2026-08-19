"""
Categoria service — business logic for category CRUD.

Key rules:
- Category names must be unique (validated before DB insert)
- A parent category must exist when parent_id is provided
- Soft-delete is blocked if active products still reference this category
"""
from typing import List, Optional
from fastapi import HTTPException, status
from app.core.routing import get_or_404
from sqlmodel import Session
from .models import Categoria
from .schemas import CategoriaCreate, CategoriaRead, CategoriaUpdate
from app.core.paginated_response import PaginatedResponse
from app.core.base import get_utc_now
from ..uow import CatalogoDeProductosUnitOfWork


def _filter_deleted_subcategorias(categories: List[Categoria]) -> None:
    """Remove soft-deleted children from each category's subcategorias list, recursively."""
    for cat in categories:
        cat.subcategorias = [c for c in cat.subcategorias if c.deleted_at is None]
        _filter_deleted_subcategorias(cat.subcategorias)


class CategoriaService:
    """Business logic for Category CRUD and validation."""

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100, parent_id: int | None = None) -> PaginatedResponse[CategoriaRead]:
        """List categories with optional parent_id filter for subtree navigation.

        Read-only: wrapped in UoW for consistent DB access.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            rows = uow.categorias.get_all(skip=skip, limit=limit, parent_id=parent_id)
            total = uow.categorias.count_all()
            return PaginatedResponse(
                items=[CategoriaRead.model_validate(r) for r in rows],
                total=total,
                skip=skip,
                limit=limit,
            )

    @staticmethod
    def get_by_id(session: Session, categoria_id: int) -> Optional[Categoria]:
        """Fetch a single non-deleted category.

        Read-only: wrapped in UoW for consistent DB access.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.categorias.get_by_id(categoria_id)

    @staticmethod
    def get_root_categories(session: Session) -> List[Categoria]:
        """Fetch all root categories (no parent) — used to build the category tree.

        Read-only: wrapped in UoW for consistent DB access.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            roots = uow.categorias.get_root_categories()
            _filter_deleted_subcategorias(roots)
            return roots

    @staticmethod
    def create(session: Session, data: CategoriaCreate) -> Categoria:
        """Create a new category.

        Validates:
        - Name uniqueness (no duplicate category names)
        - Parent category exists (FK integrity check)
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            # Validate name uniqueness before attempting DB insert
            if uow.categorias.exists_by_nombre(data.nombre):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Ya existe una categoría con el nombre '{data.nombre}'"
                )

            # Validate parent exists when specified
            if data.parent_id is not None:
                parent = uow.categorias.get_parent(data.parent_id)
                get_or_404(parent, "La categoría padre indicada no existe")

            db_categoria = Categoria(**data.model_dump())
            uow.categorias.create(db_categoria)
            return db_categoria

    @staticmethod
    def update(session: Session, categoria_id: int, data: CategoriaUpdate) -> Optional[Categoria]:
        """Update an existing category. Only provided fields are modified.
        
        Validates:
        - No self-reference (parent_id != self.id)
        - No cycles in hierarchy (walk up parent chain to detect loops)
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_categoria = uow.categorias.get_by_id(categoria_id)
            if not db_categoria:
                return None

            values = data.model_dump(exclude_unset=True)
            
            # Prevent self-reference: a category cannot be its own parent
            if "parent_id" in values and values["parent_id"] is not None:
                new_parent_id = values["parent_id"]
                
                # Direct self-reference check
                if new_parent_id == categoria_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Una categoría no puede ser padre de sí misma"
                    )
                
                # Cycle detection: walk up the new parent's chain
                # If we encounter categoria_id, setting this parent would create a cycle
                current = uow.categorias.get_by_id(new_parent_id)
                while current is not None and current.parent_id is not None:
                    if current.parent_id == categoria_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="La categoría padre seleccionada crearía un ciclo en la jerarquía"
                        )
                    current = uow.categorias.get_by_id(current.parent_id)

            for key, value in values.items():
                setattr(db_categoria, key, value)

            uow.categorias.update(db_categoria)
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
            uow.categorias.update(db_categoria)
            return db_categoria
