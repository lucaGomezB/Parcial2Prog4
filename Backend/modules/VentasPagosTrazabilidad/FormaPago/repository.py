from sqlmodel import Session, select
from .models import FormaPago


class FormaPagoRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, forma_pago: FormaPago):
        self.session.add(forma_pago)
        return forma_pago

    def get_all(self, only_habilitados: bool = False):
        statement = select(FormaPago)
        if only_habilitados:
            statement = statement.where(FormaPago.habilitado == True)
        return self.session.exec(statement).all()

    def get_by_codigo(self, codigo: str):
        statement = select(FormaPago).where(FormaPago.codigo == codigo)
        return self.session.exec(statement).first()
