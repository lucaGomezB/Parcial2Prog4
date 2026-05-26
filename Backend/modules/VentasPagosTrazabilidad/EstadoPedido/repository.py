from sqlmodel import Session, select
from models.base_repository import BaseRepository
from .models import EstadoPedido


class EstadoPedidoRepository(BaseRepository[EstadoPedido]):
    def __init__(self, session: Session):
        super().__init__(session, EstadoPedido)

    def get_all(self):
        statement = select(EstadoPedido).order_by(EstadoPedido.orden)
        return self.session.exec(statement).all()

    def get_by_codigo(self, codigo: str):
        statement = select(EstadoPedido).where(EstadoPedido.codigo == codigo)
        return self.session.exec(statement).first()
