"""
EstadoPedido service — business logic for the order status catalog.

Simple CRUD — no complex business logic. Statuses are typically created
via seed data (DB migrations). The FSM transitions are hardcoded in
PedidoService, NOT read dynamically from this table.
"""
from sqlmodel import Session
from typing import List, Optional
from .models import EstadoPedido
from .schemas import EstadoPedidoCreate, EstadoPedidoUpdate
from ..uow import VentasPagosTrazabilidadUnitOfWork


class EstadoPedidoService:
    """Business logic for the order status catalog."""

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

    @staticmethod
    def create(session: Session, data: EstadoPedidoCreate) -> EstadoPedido:
        """Create a new order status. Requires ADMIN role."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_obj = EstadoPedido(**data.model_dump())
            uow.estados.add(db_obj)
            uow.commit()
            return db_obj

    @staticmethod
    def update(session: Session, codigo: str, data: EstadoPedidoUpdate) -> Optional[EstadoPedido]:
        """Update an existing order status. Only provided fields are modified."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_obj = uow.estados.get_by_codigo(codigo)
            if not db_obj:
                return None
            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(db_obj, key, value)
            uow.estados.add(db_obj)
            uow.commit()
            return db_obj

    @staticmethod
    def delete(session: Session, codigo: str) -> bool:
        """Delete an order status.

        Cannot delete a status that is referenced by existing orders (FK constraint).
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_obj = uow.estados.get_by_codigo(codigo)
            if not db_obj:
                return False
            uow.session.delete(db_obj)
            uow.commit()
            return True
