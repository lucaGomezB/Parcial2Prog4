from sqlmodel import Session

from .models import Rol
from models.base_repository import BaseRepository


class RolRepository(BaseRepository[Rol]):
    def __init__(self, session: Session):
        super().__init__(session, Rol)

    def get_by_codigo(self, codigo: str) -> Rol | None:
        return self.session.get(Rol, codigo)
