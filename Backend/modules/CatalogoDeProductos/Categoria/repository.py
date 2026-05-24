from sqlmodel import Session, col, select

from .models import Categoria


class CategoriaRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, categoria: Categoria):
        self.session.add(categoria)
        return categoria

    def refresh(self, categoria: Categoria):
        self.session.refresh(categoria)
        return categoria

    def get_root_categories(self):
        statement = select(Categoria).where(col(Categoria.parent_id).is_(None), col(Categoria.deleted_at).is_(None))
        return self.session.exec(statement).all()

    def get_by_id(self, categoria_id: int):
        statement = select(Categoria).where(Categoria.id == categoria_id, col(Categoria.deleted_at).is_(None))
        return self.session.exec(statement).first()

    def get_all(self, skip: int = 0, limit: int = 100):
        statement = select(Categoria).where(col(Categoria.deleted_at).is_(None)).offset(skip).limit(limit)
        return self.session.exec(statement).all()
