from sqlmodel import Session

from models.base_repository import BaseRepository
from .models import Ingrediente


class IngredienteRepository(BaseRepository[Ingrediente]):
    def __init__(self, session: Session):
        super().__init__(session, Ingrediente)
