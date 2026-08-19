"""
UnidadMedida service — business logic for measurement unit management.

Design decisions:
    - Static methods receiving session (matches existing pattern in the project)
    - DELETE checks FK references before attempting deletion (design D5, risk mitigation)
    - Immutable catalog: no updated_at logic needed (D4)
    - ALL DB operations (read and write) go through the Unit of Work.
"""
from sqlmodel import Session
from typing import Optional, List
from fastapi import HTTPException

from .models import UnidadMedida
from .schemas import UnidadMedidaCreate, UnidadMedidaUpdate
from ..uow import CatalogoDeProductosUnitOfWork


class UnidadMedidaService:
    """Business logic for measurement unit CRUD operations."""

    @staticmethod
    def get_all(session: Session, tipo_filter: Optional[str] = None) -> List[UnidadMedida]:
        """List all units, optionally filtered by tipo."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.unidades_medida.get_all(tipo_filter=tipo_filter)

    @staticmethod
    def get_by_id(session: Session, unidad_id: int) -> Optional[UnidadMedida]:
        """Retrieve a single unit by its ID. Returns None if not found."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.unidades_medida.get_by_id(unidad_id)

    @staticmethod
    def create(session: Session, data: UnidadMedidaCreate) -> UnidadMedida:
        """Create a new measurement unit. Returns the created unit with generated id."""
        if data.factor_conversion <= 0:
            raise HTTPException(
                status_code=422,
                detail="El factor de conversion debe ser mayor que cero.",
            )
        with CatalogoDeProductosUnitOfWork(session) as uow:
            # Prevent duplicate base unit for the same tipo
            if data.factor_conversion == 1:
                existing = uow.unidades_medida.find_base_by_tipo(data.tipo)
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Ya existe una unidad base para el tipo '{data.tipo}': "
                               f"{existing.nombre} ({existing.simbolo})",
                    )
            unit = UnidadMedida(
                nombre=data.nombre,
                simbolo=data.simbolo,
                tipo=data.tipo,
                factor_conversion=data.factor_conversion,
            )
            uow.unidades_medida.create(unit)
            return unit

    @staticmethod
    def update(session: Session, unidad_id: int, data: UnidadMedidaUpdate) -> Optional[UnidadMedida]:
        """Update a measurement unit. Only provided (non-None) fields are changed.

        Returns the updated unit, or None if the unit does not exist.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            unit = uow.unidades_medida.get_by_id(unidad_id)
            if not unit:
                return None

            update_data = data.model_dump(exclude_unset=True)

            # Validate factor_conversion > 0 if present
            if "factor_conversion" in update_data and update_data["factor_conversion"] <= 0:
                raise HTTPException(
                    status_code=422,
                    detail="El factor de conversion debe ser mayor que cero.",
                )

            # Prevent setting factor_conversion to 1 if base already exists for tipo
            if update_data.get("factor_conversion") == 1:
                search_tipo = update_data.get("tipo", unit.tipo)
                existing = uow.unidades_medida.find_base_by_tipo(search_tipo)
                if existing and existing.id != unidad_id:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Ya existe una unidad base para el tipo '{existing.tipo}': "
                               f"{existing.nombre} ({existing.simbolo})",
                    )

            for field, value in update_data.items():
                setattr(unit, field, value)

            uow.unidades_medida.update(unit)
            return unit

    @staticmethod
    def delete(session: Session, unidad_id: int) -> bool:
        """Delete a measurement unit. Fails if the unit has FK references.

        Returns True if deleted, False if not found.
        Raises ValueError if the unit is referenced by any Producto or
        ProductoIngrediente (FK protection per spec).
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            unit = uow.unidades_medida.get_by_id(unidad_id)
            if not unit:
                return False

            if uow.unidades_medida.has_references(unidad_id):
                raise ValueError(
                    f"La unidad de medida '{unit.nombre}' está en uso y no puede ser eliminada"
                )

            uow.delete(unit)
            uow.flush()
            return True
