"""
FormaPago repository — data access layer for payment method catalog.

Provides queries to fetch enabled-only methods or all methods.
"""
from sqlmodel import Session, select
from models.base_repository import BaseRepository
from .models import FormaPago


class FormaPagoRepository(BaseRepository[FormaPago]):
    """Repository for FormaPago with catalog queries."""

    def __init__(self, session: Session):
        super().__init__(session, FormaPago)

    def get_all(self, only_habilitados: bool = False):
        """Return all payment methods, optionally filtering to enabled ones only."""
        statement = select(FormaPago)
        if only_habilitados:
            statement = statement.where(FormaPago.habilitado == True)
        return self.session.exec(statement).all()

    def get_by_codigo(self, codigo: str):
        """Fetch a single payment method by its code."""
        statement = select(FormaPago).where(FormaPago.codigo == codigo)
        return self.session.exec(statement).first()
