from sqlmodel import Session, col, select

from models.base_repository import BaseRepository
from .models import Categoria


class CategoriaRepository(BaseRepository[Categoria]):
    def __init__(self, session: Session):
        super().__init__(session, Categoria)

    def get_root_categories(self):
        statement = select(Categoria).where(col(Categoria.parent_id).is_(None), col(Categoria.deleted_at).is_(None))
        return self.session.exec(statement).all()

    def get_by_id(self, categoria_id: int):
        statement = select(Categoria).where(Categoria.id == categoria_id, col(Categoria.deleted_at).is_(None))
        return self.session.exec(statement).first()

    def get_all(self, skip: int = 0, limit: int = 100, parent_id: int | None = None):
        statement = select(Categoria).where(col(Categoria.deleted_at).is_(None))
        if parent_id is not None:
            statement = statement.where(Categoria.parent_id == parent_id)
        statement = statement.offset(skip).limit(limit)
        return self.session.exec(statement).all()
