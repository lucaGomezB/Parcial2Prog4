"""
HistorialStock repository — data access for stock audit log.
"""
from typing import List
from sqlmodel import Session, select
from app.core.base_repository import BaseRepository
from .models import HistorialStock


class HistorialStockRepository(BaseRepository[HistorialStock]):
    """Repository for HistorialStock (append-only audit log)."""

    def __init__(self, session: Session):
        super().__init__(session, HistorialStock)

    def create(self, historial: HistorialStock) -> HistorialStock:
        """Insert a new HistorialStock row and refresh to get generated id."""
        self.session.add(historial)
        self.session.flush()
        self.session.refresh(historial)
        return historial

    def get_by_entidad(
        self,
        session: Session,
        entidad_tipo: str,
        entidad_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HistorialStock]:
        """Return paginated stock history for a given entity, newest first."""
        statement = (
            select(HistorialStock)
            .where(
                HistorialStock.entidad_tipo == entidad_tipo,
                HistorialStock.entidad_id == entidad_id,
            )
            .offset(skip)
            .limit(limit)
            .order_by(HistorialStock.created_at.desc())
        )
        return self.session.exec(statement).all()
