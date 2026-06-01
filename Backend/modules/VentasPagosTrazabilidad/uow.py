"""
Unit of Work for the VentasPagosTrazabilidad module.

Provides a transactional boundary around all order-related repositories.
Pure persistence coordination — no business logic or domain operations.
State transitions (avanzar_estado) are managed by PedidoService.
"""
from sqlmodel import Session
from .EstadoPedido.repository import EstadoPedidoRepository
from .FormaPago.repository import FormaPagoRepository
from .Pedido.repository import PedidoRepository
from .DetallePedido.repository import DetallePedidoRepository
from .HistorialEstadoPedido.repository import HistorialEstadoPedidoRepository
from .Pago.repository import PagoRepository


class VentasPagosTrazabilidadUnitOfWork:
    """Unit of Work for the Sales/Payments module.

    Provides repositories and transaction management only.
    Domain coordination (e.g., state transitions) lives in the services.
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
