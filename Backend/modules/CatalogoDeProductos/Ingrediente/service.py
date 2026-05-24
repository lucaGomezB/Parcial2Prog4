from sqlmodel import Session
from typing import List, Optional
from .models import Ingrediente
from .schemas import IngredienteCreate, IngredienteUpdate
from models.base import get_utc_now
from ..uow import CatalogoDeProductosUnitOfWork

class IngredienteService:
    @staticmethod
    def create(session: Session, data: IngredienteCreate) -> Ingrediente:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = Ingrediente.model_validate(data)
            uow.ingredientes.add(db_ingrediente)
            uow.commit()
            uow.ingredientes.refresh(db_ingrediente)
            return db_ingrediente

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100) -> List[Ingrediente]:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.ingredientes.get_all(skip=skip, limit=limit)

    @staticmethod
    def get_by_id(session: Session, ingrediente_id: int) -> Optional[Ingrediente]:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.ingredientes.get_by_id(ingrediente_id)

    @staticmethod
    def update(session: Session, ingrediente_id: int, data: IngredienteUpdate) -> Optional[Ingrediente]:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            if not db_ingrediente:
                return None

            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(db_ingrediente, key, value)

            uow.ingredientes.add(db_ingrediente)
            uow.commit()
            uow.ingredientes.refresh(db_ingrediente)
            return db_ingrediente

    @staticmethod
    def soft_delete(session: Session, ingrediente_id: int) -> bool:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            if not db_ingrediente:
                return False

            db_ingrediente.deleted_at = get_utc_now()
            uow.ingredientes.add(db_ingrediente)
            uow.commit()
            return True