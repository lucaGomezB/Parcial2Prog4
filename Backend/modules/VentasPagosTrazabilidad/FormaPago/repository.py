from sqlmodel import Session, select
from models.base_repository import BaseRepository
from .models import FormaPago


class FormaPagoRepository(BaseRepository[FormaPago]):
    def __init__(self, session: Session):
        super().__init__(session, FormaPago)

    def get_all(self, only_habilitados: bool = False):
        statement = select(FormaPago)
        if only_habilitados:
            statement = statement.where(FormaPago.habilitado == True)
        return self.session.exec(statement).all()

    def get_by_codigo(self, codigo: str):
        statement = select(FormaPago).where(FormaPago.codigo == codigo)
        return self.session.exec(statement).first()
