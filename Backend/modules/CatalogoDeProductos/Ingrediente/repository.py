from sqlmodel import Session, col, select

from .models import Ingrediente


class IngredienteRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, ingrediente: Ingrediente):
        self.session.add(ingrediente)
        return ingrediente

    def refresh(self, ingrediente: Ingrediente):
        self.session.refresh(ingrediente)
        return ingrediente

    def get_all(self, skip: int = 0, limit: int = 100):
        statement = select(Ingrediente).where(col(Ingrediente.deleted_at).is_(None)).offset(skip).limit(limit)
        return self.session.exec(statement).all()

    def get_by_id(self, ingrediente_id: int):
        statement = select(Ingrediente).where(Ingrediente.id == ingrediente_id, col(Ingrediente.deleted_at).is_(None))
        return self.session.exec(statement).first()
