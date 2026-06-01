"""
EstadoPedido repository — data access layer for order status catalog.

Provides queries ordered by the 'orden' display field.
"""
from sqlmodel import Session, select
from models.base_repository import BaseRepository
from .models import EstadoPedido


class EstadoPedidoRepository(BaseRepository[EstadoPedido]):
    """Repository for EstadoPedido with status-catalog queries."""

    def __init__(self, session: Session):
        super().__init__(session, EstadoPedido)

    def get_all(self):
        """Return all statuses ordered by display order."""
        statement = select(EstadoPedido).order_by(EstadoPedido.orden)
        return self.session.exec(statement).all()

    def get_by_codigo(self, codigo: str):
        """Fetch a single status by its semantic code."""
        statement = select(EstadoPedido).where(EstadoPedido.codigo == codigo)
        return self.session.exec(statement).first()
