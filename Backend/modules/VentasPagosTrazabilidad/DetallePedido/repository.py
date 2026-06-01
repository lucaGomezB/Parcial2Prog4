"""
DetallePedido repository — data access layer for order detail lines.

Provides a query to fetch all details for a given order.
"""
from sqlmodel import Session, select
from typing import List
from models.base_repository import BaseRepository
from .models import DetallePedido


class DetallePedidoRepository(BaseRepository[DetallePedido]):
    """Repository for DetallePedido with order-specific queries."""

    def __init__(self, session: Session):
        super().__init__(session, DetallePedido)

    def get_by_pedido(self, pedido_id: int) -> List[DetallePedido]:
        """Return all detail lines for a given order, ordered by creation time."""
        statement = select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)
        return self.session.exec(statement).all()
