from sqlmodel import Session, select, col
from typing import List
from models.base_repository import BaseRepository
from .models import Pedido


class PedidoRepository(BaseRepository[Pedido]):
    def __init__(self, session: Session):
        super().__init__(session, Pedido)

    def get_by_usuario_id(self, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        statement = (
            select(Pedido)
            .where(Pedido.usuario_id == usuario_id, col(Pedido.deleted_at).is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.id.desc())
        )
        return self.session.exec(statement).all()
