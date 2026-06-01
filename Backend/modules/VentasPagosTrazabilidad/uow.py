"""
Unit of Work for the VentasPagosTrazabilidad module.

Provides a transactional boundary around all order-related repositories.
Also exposes helper methods for atomic state transitions (avanzar_estado)
that combine Pedido update + HistorialEstadoPedido insert in a single operation.
"""
from sqlmodel import Session
from .EstadoPedido.repository import EstadoPedidoRepository
from .FormaPago.repository import FormaPagoRepository
from .Pedido.repository import PedidoRepository
from .DetallePedido.repository import DetallePedidoRepository
from .HistorialEstadoPedido.repository import HistorialEstadoPedidoRepository
from .HistorialEstadoPedido.models import HistorialEstadoPedido
from .Pago.repository import PagoRepository


class VentasPagosTrazabilidadUnitOfWork:
    """Unit of Work for the Sales/Payments module.

    Usage:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            uow.pedidos.add(...)
            uow.add(entity)
            uow.commit()
    """

    def __init__(self, session: Session):
        self.session = session
        self.estados = EstadoPedidoRepository(session)
        self.formas_pago = FormaPagoRepository(session)
        self.pedidos = PedidoRepository(session)
        self.detalles = DetallePedidoRepository(session)
        self.historial = HistorialEstadoPedidoRepository(session)
        self.pagos = PagoRepository(session)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        return False

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

    def add(self, entity):
        """Generic add for any entity (DetallePedido, HistorialEstadoPedido, etc)."""
        self.session.add(entity)
        return entity

    def flush(self):
        """Flush pending changes to DB to obtain generated IDs without committing."""
        self.session.flush()

    def refresh(self, entity):
        """Reload entity from DB after flush/commit to get latest values."""
        self.session.refresh(entity)
        return entity

    def delete(self, entity):
        """Mark an entity for deletion on next flush/commit."""
        self.session.delete(entity)

    def avanzar_estado(self, pedido, estado_anterior, estado_siguiente, usuario_id=None, motivo=None):
        """Atomic state transition: UPDATE Pedido + INSERT HistorialEstadoPedido.

        This is the core method for FSM transitions. It combines two operations:
        1. INSERT a new HistorialEstadoPedido row (append-only audit log)
        2. UPDATE the Pedido's estado_codigo

        Params:
            - pedido: the Pedido ORM instance
            - estado_anterior: previous state (None = creation / seed state)
            - estado_siguiente: target state
            - usuario_id: who triggered the transition (None = system/webhook)
            - motivo: optional reason (e.g. "Cancelado por usuario")

        Note: commit() is delegated to __exit__ of the context manager.
        """
        # INSERT historial row (APPEND ONLY — never modified after creation)
        self.session.add(HistorialEstadoPedido(
            pedido_id=pedido.id,
            estado_desde=estado_anterior,   # None indicates creation
            estado_hacia=estado_siguiente,
            usuario_id=usuario_id,           # None indicates system action
            motivo=motivo,
        ))

        # UPDATE pedido's current state
        pedido.estado_codigo = estado_siguiente
        self.pedidos.add(pedido)

        return pedido
