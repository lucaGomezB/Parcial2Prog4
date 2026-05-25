from sqlmodel import Session

from .DireccionEntrega.repository import DireccionEntregaRepository


class IdentidadYAccesoUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.direcciones = DireccionEntregaRepository(session)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        return False

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
