"""
Unit of Work for the VentasPagosTrazabilidad module.

Provides a transactional boundary around all order-related repositories.
Pure persistence coordination — no business logic or domain operations.
State transitions (avanzar_estado) are managed by PedidoService.
"""
from sqlmodel import Session
from app.core.base_uow import BaseUnitOfWork

from .EstadoPedido.repository import EstadoPedidoRepository
from .FormaPago.repository import FormaPagoRepository
from .Pedido.repository import PedidoRepository
from .DetallePedido.repository import DetallePedidoRepository
from .HistorialEstadoPedido.repository import HistorialEstadoPedidoRepository
from .Pago.repository import PagoRepository
from .CarritoSnapshot.repository import CarritoSnapshotRepository


class VentasPagosTrazabilidadUnitOfWork(BaseUnitOfWork):
    """Unit of Work for the Sales/Payments module.

    Provides repositories and transaction management only.
    Domain coordination (e.g., state transitions) lives in the services.
    """

    def __init__(self, session: Session):
        super().__init__(session)
        self.estados = EstadoPedidoRepository(session)
        self.formas_pago = FormaPagoRepository(session)
        self.pedidos = PedidoRepository(session)
        self.detalles = DetallePedidoRepository(session)
        self.historial = HistorialEstadoPedidoRepository(session)
        self.pagos = PagoRepository(session)
        self.snapshots = CarritoSnapshotRepository(session)
