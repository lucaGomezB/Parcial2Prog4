"""
HistorialEstadoPedido repository — data access layer for order state history.

Provides query to fetch the full audit trail for a given order, ordered
chronologically, and a paginated listing with optional pedido_id filter.
"""
from sqlmodel import Session, select
from typing import List, Optional
from app.core.base_repository import BaseRepository
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

    def get_all_paginated(
        self,
        skip: int = 0,
        limit: int = 100,
        pedido_id: Optional[int] = None,
    ) -> List[HistorialEstadoPedido]:
        """Paginated list of history entries, newest first.

        If pedido_id is provided, filters to entries for that specific order.
        Ordered by created_at DESC to show most recent transitions first.
        """
        statement = select(HistorialEstadoPedido)
        if pedido_id is not None:
            statement = statement.where(HistorialEstadoPedido.pedido_id == pedido_id)
        statement = (
            statement
            .offset(skip)
            .limit(limit)
            .order_by(HistorialEstadoPedido.created_at.desc())
        )
        return self.session.exec(statement).all()
