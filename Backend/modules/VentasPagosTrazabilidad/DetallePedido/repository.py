from sqlmodel import Session, select
from typing import List
from models.base_repository import BaseRepository
from .models import DetallePedido


class DetallePedidoRepository(BaseRepository[DetallePedido]):
    def __init__(self, session: Session):
        super().__init__(session, DetallePedido)

    def get_by_pedido(self, pedido_id: int) -> List[DetallePedido]:
        statement = select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)
        return self.session.exec(statement).all()
