"""
Unit of Work for the Estadisticas module.

Provides a transactional boundary for analytics queries.
All read operations are wrapped in a UoW for consistency.
"""
from sqlmodel import Session
from app.core.base_uow import BaseUnitOfWork
from .repository import EstadisticasRepository


class EstadisticasUnitOfWork(BaseUnitOfWork):
    """Unit of Work for the Estadisticas (analytics) module."""

    def __init__(self, session: Session):
        super().__init__(session)
        self.estadisticas = EstadisticasRepository(session)
