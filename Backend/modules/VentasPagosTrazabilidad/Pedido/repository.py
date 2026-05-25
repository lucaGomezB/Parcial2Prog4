from sqlmodel import Session, select, col
from typing import List, Optional
from .models import Pedido


class PedidoRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, pedido: Pedido):
        self.session.add(pedido)
        return pedido

    def refresh(self, pedido: Pedido):
        self.session.refresh(pedido)
        return pedido

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Pedido]:
        statement = (
            select(Pedido)
            .where(col(Pedido.deleted_at).is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.id.desc())
        )
        return self.session.exec(statement).all()

    def get_by_id(self, pedido_id: int) -> Optional[Pedido]:
        statement = select(Pedido).where(Pedido.id == pedido_id, col(Pedido.deleted_at).is_(None))
        return self.session.exec(statement).first()

    def get_by_usuario_id(self, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        statement = (
            select(Pedido)
            .where(Pedido.usuario_id == usuario_id, col(Pedido.deleted_at).is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.id.desc())
        )
        return self.session.exec(statement).all()
