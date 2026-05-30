from sqlmodel import Session
from .EstadoPedido.repository import EstadoPedidoRepository
from .FormaPago.repository import FormaPagoRepository
from .Pedido.repository import PedidoRepository
from .DetallePedido.repository import DetallePedidoRepository
from .HistorialEstadoPedido.repository import HistorialEstadoPedidoRepository
from .HistorialEstadoPedido.models import HistorialEstadoPedido
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

    def add(self, entity):
        """Generic add for any entity (DetallePedido, HistorialEstadoPedido, etc)."""
        self.session.add(entity)
        return entity

    def flush(self):
        """Flush pending changes to DB (to get IDs without committing)."""
        self.session.flush()

    def refresh(self, entity):
        """Reload entity from DB after flush/commit."""
        self.session.refresh(entity)
        return entity

    def delete(self, entity):
        """Mark an entity for deletion on next flush/commit."""
        self.session.delete(entity)

    def avanzar_estado(self, pedido, estado_anterior, estado_siguiente, usuario_id=None, motivo=None):
        """Transición atómica de estado: UPDATE Pedido + INSERT HistorialEstadoPedido.

        - estado_anterior=None → creación del pedido (estado semilla)
        - usuario_id=None → actor es el sistema (webhook)

        commit() se delega a __exit__ del context manager.
        """
        # INSERT historial (APPEND ONLY)
        self.session.add(HistorialEstadoPedido(
            pedido_id=pedido.id,
            estado_desde=estado_anterior,   # None = creación
            estado_hacia=estado_siguiente,
            usuario_id=usuario_id,           # None = sistema
            motivo=motivo,
        ))

        # UPDATE pedido
        pedido.estado_codigo = estado_siguiente
        self.pedidos.add(pedido)

        return pedido
