"""
Ingrediente service — business logic for ingredient CRUD.

Key behaviors:
- Price changes trigger automatic recalculation of all affected product prices
- Duplicate ingredient names are caught via IntegrityError
- Read operations avoid UoW to prevent ORM object expiration
- Stock and price have dedicated update endpoints with side effects
"""
from decimal import Decimal

from sqlmodel import Session
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from .models import Ingrediente
from .repository import IngredienteRepository
from .schemas import IngredienteCreate, IngredienteRead, IngredienteUpdate
from core.paginated_response import PaginatedResponse
from models.base import get_utc_now
from ..uow import CatalogoDeProductosUnitOfWork
from ..Producto.service import ProductoService


class IngredienteService:
    """Business logic for Ingredient CRUD and automatic price propagation."""

    @staticmethod
    def create(session: Session, data: IngredienteCreate) -> Ingrediente:
        """Create a new ingredient with duplicate name handling."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = Ingrediente.model_validate(data)
            uow.ingredientes.add(db_ingrediente)
            try:
                uow.flush()
            except IntegrityError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe un ingrediente con ese nombre. No se puede crear duplicados.",
                )
            uow.ingredientes.refresh(db_ingrediente)
            return db_ingrediente

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100) -> PaginatedResponse[IngredienteRead]:
        """List non-deleted ingredients with pagination.

        Read-only: uses repository directly (no UoW) to avoid commit/expire.
        """
        repo = IngredienteRepository(session)
        rows = repo.get_all_paginated(skip=skip, limit=limit)
        total = repo.count_all()
        return PaginatedResponse(
            items=[IngredienteRead.model_validate(r) for r in rows],
            total=total,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_by_id(session: Session, ingrediente_id: int) -> Optional[IngredienteRead]:
        """Fetch a single non-deleted ingredient by ID.

        Read-only: uses repository directly (no UoW).
        """
        repo = IngredienteRepository(session)
        row = repo.get_by_id(ingrediente_id)
        if not row:
            return None
        return IngredienteRead.model_validate(row)

    @staticmethod
    def actualizar_precio(session: Session, ingrediente_id: int, precio: Decimal) -> Ingrediente:
        """Update ingredient price and trigger recalculation of all affected products.

        This is the key method that propagates ingredient price changes
        through the product catalog.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            if not db_ingrediente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ingrediente no encontrado",
                )
            db_ingrediente.precio_actual = precio
            uow.ingredientes.add(db_ingrediente)
        # Refresh after commit to get current state
        session.refresh(db_ingrediente)
        # Trigger price recalculation for all products using this ingredient
        ProductoService.recalcular_precio_productos_afectados(session, ingrediente_id)
        return db_ingrediente

    @staticmethod
    def actualizar_stock(session: Session, ingrediente_id: int, stock: int) -> Ingrediente:
        """Update ingredient stock. Does NOT affect product prices."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            if not db_ingrediente:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ingrediente no encontrado",
                )
            db_ingrediente.stock_actual = stock
            uow.ingredientes.add(db_ingrediente)
        # Refresh after commit to get current state
        session.refresh(db_ingrediente)
        return db_ingrediente

    @staticmethod
    def update(session: Session, ingrediente_id: int, data: IngredienteUpdate) -> Optional[Ingrediente]:
        """Update an ingredient. Triggers price recalculation if precio_actual changed."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            if not db_ingrediente:
                return None

            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(db_ingrediente, key, value)

            uow.ingredientes.add(db_ingrediente)
        # Propagate price change to all products if precio_actual was updated
        if 'precio_actual' in data.model_dump(exclude_unset=True):
            ProductoService.recalcular_precio_productos_afectados(session, ingrediente_id)
        # Refresh after commit to load auto-generated timestamps without discarding changes
        session.refresh(db_ingrediente)
        return db_ingrediente

    @staticmethod
    def soft_delete(session: Session, ingrediente_id: int) -> bool:
        """Soft-delete an ingredient. Returns True if deleted, False if not found."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            if not db_ingrediente:
                return False

            db_ingrediente.deleted_at = get_utc_now()
            uow.ingredientes.add(db_ingrediente)
            return True
