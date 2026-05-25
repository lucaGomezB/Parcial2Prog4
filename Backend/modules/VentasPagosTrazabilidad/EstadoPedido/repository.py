from sqlmodel import Session, select
from .models import EstadoPedido


class EstadoPedidoRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, estado: EstadoPedido):
        self.session.add(estado)
        return estado

    def get_all(self):
        statement = select(EstadoPedido).order_by(EstadoPedido.orden)
        return self.session.exec(statement).all()

    def get_by_codigo(self, codigo: str):
        statement = select(EstadoPedido).where(EstadoPedido.codigo == codigo)
        return self.session.exec(statement).first()
