"""
HistorialEstadoPedido service — read-only access to order state history.

Read operations do NOT use UoW to avoid the commit/expire problem.
All queries delegate to the repository.
"""
from typing import List, Optional
from sqlmodel import Session
from .models import HistorialEstadoPedido
from .repository import HistorialEstadoPedidoRepository


class HistorialEstadoPedidoService:
    """Read-only business logic for order state history."""

    @staticmethod
    def get_by_pedido(session: Session, pedido_id: int) -> List[HistorialEstadoPedido]:
        """Return the full history trail for an order, oldest to newest.

        Delegates directly to the repository without UoW since this is
        a read-only operation. Avoiding UoW prevents the commit/expire
        problem that would expire ORM objects before serialization.
        """
        repo = HistorialEstadoPedidoRepository(session)
        return repo.get_by_pedido(pedido_id)

    @staticmethod
    def get_by_id(session: Session, history_id: int) -> Optional[HistorialEstadoPedido]:
        """Fetch a single history entry by its primary key.

        Returns None if no record matches the given ID.
        Uses repository directly (read-only, no UoW needed).
        """
        repo = HistorialEstadoPedidoRepository(session)
        return repo.get_by_id(history_id)

    @staticmethod
    def get_all(
        session: Session,
        skip: int = 0,
        limit: int = 100,
        pedido_id: Optional[int] = None,
    ) -> List[HistorialEstadoPedido]:
        """Paginated list of history entries, newest first.

        If pedido_id is provided, filters to entries for that specific order.
        Ordered by created_at DESC to show most recent transitions first.
        Delegates to repository (read-only, no UoW).

        Args:
            session: Active SQLModel database session.
            skip: Number of records to skip (pagination offset).
            limit: Maximum number of records to return.
            pedido_id: Optional order ID to filter by.

        Returns:
            List of HistorialEstadoPedido records matching the criteria.
        """
        repo = HistorialEstadoPedidoRepository(session)
        return repo.get_all_paginated(skip=skip, limit=limit, pedido_id=pedido_id)
