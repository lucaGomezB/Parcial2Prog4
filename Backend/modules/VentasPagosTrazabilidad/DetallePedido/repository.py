from sqlmodel import Session, select
from typing import List
from .models import DetallePedido


class DetallePedidoRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, detalle: DetallePedido):
        self.session.add(detalle)
        return detalle

    def get_by_pedido(self, pedido_id: int) -> List[DetallePedido]:
        statement = select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)
        return self.session.exec(statement).all()
