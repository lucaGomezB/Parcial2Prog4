"""
HistorialEstadoPedido repository — data access layer for order state history.

Provides query to fetch the full audit trail for a given order, ordered chronologically.
"""
from sqlmodel import Session, select
from typing import List
from models.base_repository import BaseRepository
from .models import HistorialEstadoPedido


class HistorialEstadoPedidoRepository(BaseRepository[HistorialEstadoPedido]):
    """Repository for HistorialEstadoPedido (append-only audit log)."""

    def __init__(self, session: Session):
        super().__init__(session, HistorialEstadoPedido)

    def get_by_pedido(self, pedido_id: int) -> List[HistorialEstadoPedido]:
        """Return the full history trail for an order, oldest to newest."""
        statement = (
            select(HistorialEstadoPedido)
            .where(HistorialEstadoPedido.pedido_id == pedido_id)
            .order_by(HistorialEstadoPedido.created_at.asc())
        )
        return self.session.exec(statement).all()
