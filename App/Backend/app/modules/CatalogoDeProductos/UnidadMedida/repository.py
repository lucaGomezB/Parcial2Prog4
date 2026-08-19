"""
UnidadMedida repository — data access layer for measurement units.

Extends BaseRepository with tipo-based filtering and FK reference checking.
"""
from sqlmodel import Session, select
from typing import List, Optional

from app.core.base_repository import BaseRepository
from .models import UnidadMedida


class UnidadMedidaRepository(BaseRepository[UnidadMedida]):
    """Repository for UnidadMedida with tipo filtering and FK protection."""

    def __init__(self, session: Session):
        super().__init__(session, UnidadMedida)

    def get_all(self, tipo_filter: Optional[str] = None) -> List[UnidadMedida]:
        """List all units ordered by tipo then nombre.

        Args:
            tipo_filter: Optional tipo value to filter by (e.g., "masa").
        """
        statement = select(UnidadMedida)
        if tipo_filter:
            statement = statement.where(UnidadMedida.tipo == tipo_filter)
        statement = statement.order_by(UnidadMedida.tipo, UnidadMedida.nombre)
        return self.session.exec(statement).all()

    def get_by_id(self, entity_id: int) -> Optional[UnidadMedida]:
        """Retrieve a single unit by its surrogate ID."""
        statement = select(UnidadMedida).where(UnidadMedida.id == entity_id)
        return self.session.exec(statement).first()

    def find_base_by_tipo(self, tipo: str) -> Optional[UnidadMedida]:
        """Find the base unit (factor_conversion = 1) for a given tipo.

        Args:
            tipo: The measurement type to search for (e.g., "masa", "volumen").

        Returns:
            The base UnidadMedida if found, None otherwise.
        """
        statement = (
            select(UnidadMedida)
            .where(UnidadMedida.tipo == tipo)
            .where(UnidadMedida.factor_conversion == 1)
        )
        return self.session.exec(statement).first()

    def has_references(self, unidad_id: int) -> bool:
        """Check whether any Producto or ProductoIngrediente references this unit."""
        from ..Producto.models import Producto
        from ..producto_ingrediente import ProductoIngrediente

        # Check producto references
        prod_stmt = (
            select(Producto)
            .where(Producto.unidad_medida_id == unidad_id)
            .limit(1)
        )
        if self.session.exec(prod_stmt).first():
            return True

        # Check productoingrediente references
        pi_stmt = (
            select(ProductoIngrediente)
            .where(ProductoIngrediente.unidad_medida_id == unidad_id)
            .limit(1)
        )
        if self.session.exec(pi_stmt).first():
            return True

        return False
