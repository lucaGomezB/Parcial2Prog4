from sqlmodel import Session, select
from typing import List
from .models import HistorialEstadoPedido


class HistorialEstadoPedidoRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, historial: HistorialEstadoPedido):
        self.session.add(historial)
        return historial

    def get_by_pedido(self, pedido_id: int) -> List[HistorialEstadoPedido]:
        statement = (
            select(HistorialEstadoPedido)
            .where(HistorialEstadoPedido.pedido_id == pedido_id)
            .order_by(HistorialEstadoPedido.created_at.asc())
        )
        return self.session.exec(statement).all()
