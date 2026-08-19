"""
EstadoPedido service — read-only access for the order status catalog.

Statuses are created exclusively via seed data. The FSM transitions
are hardcoded in PedidoService. This service only provides lookup
methods for internal use by other services.
"""
from sqlmodel import Session
from typing import List, Optional
from .models import EstadoPedido
from ..uow import VentasPagosTrazabilidadUnitOfWork


class EstadoPedidoService:
    """Read-only access to the order status catalog."""

    @staticmethod
    def get_all(session: Session) -> List[EstadoPedido]:
        """List all order statuses, ordered by display order."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.estados.get_all()

    @staticmethod
    def get_by_codigo(session: Session, codigo: str) -> Optional[EstadoPedido]:
        """Fetch a single status by its code (e.g. 'PENDIENTE', 'CONFIRMADO')."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.estados.get_by_codigo(codigo)
