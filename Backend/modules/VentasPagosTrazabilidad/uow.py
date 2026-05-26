from sqlmodel import Session
from .EstadoPedido.repository import EstadoPedidoRepository
from .FormaPago.repository import FormaPagoRepository
from .Pedido.repository import PedidoRepository
from .DetallePedido.repository import DetallePedidoRepository
from .HistorialEstadoPedido.repository import HistorialEstadoPedidoRepository
from .Pago.repository import PagoRepository


class VentasPagosTrazabilidadUnitOfWork:
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
