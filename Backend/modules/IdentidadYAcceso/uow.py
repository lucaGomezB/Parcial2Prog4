from sqlmodel import Session

from .Auth.repository import RefreshTokenRepository
from .DireccionEntrega.repository import DireccionEntregaRepository
from .Rol.repository import RolRepository
from .Usuario.repository import UsuarioRepository


class IdentidadYAccesoUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.direcciones = DireccionEntregaRepository(session)
        self.usuarios = UsuarioRepository(session)
        self.roles = RolRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        return False

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
