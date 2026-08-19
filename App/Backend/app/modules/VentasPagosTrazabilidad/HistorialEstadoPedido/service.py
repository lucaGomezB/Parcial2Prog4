"""
HistorialEstadoPedido service — read-only access to order state history.

All operations go through VentasPagosTrazabilidadUnitOfWork.
"""
from typing import List, Optional
from sqlmodel import Session
from .models import HistorialEstadoPedido
from ..uow import VentasPagosTrazabilidadUnitOfWork


class HistorialEstadoPedidoService:
    """Read-only business logic for order state history."""

    @staticmethod
    def get_by_pedido(session: Session, pedido_id: int) -> List[HistorialEstadoPedido]:
        """Return the full history trail for an order, oldest to newest."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.historial.get_by_pedido(pedido_id)

    @staticmethod
    def get_by_id(session: Session, history_id: int) -> Optional[HistorialEstadoPedido]:
        """Fetch a single history entry by its primary key.

        Returns None if no record matches the given ID.
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.historial.get_by_id(history_id)

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

        Args:
            session: Active SQLModel database session.
            skip: Number of records to skip (pagination offset).
            limit: Maximum number of records to return.
            pedido_id: Optional order ID to filter by.

        Returns:
            List of HistorialEstadoPedido records matching the criteria.
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.historial.get_all_paginated(skip=skip, limit=limit, pedido_id=pedido_id)
