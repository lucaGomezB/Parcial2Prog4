from typing import List, Optional
from sqlmodel import Session
from .models import Categoria
from .schemas import CategoriaCreate, CategoriaUpdate
from models.base import get_utc_now
from ..uow import CatalogoDeProductosUnitOfWork


class CategoriaService:
    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100) -> List[Categoria]:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.categorias.get_all(skip=skip, limit=limit)

    @staticmethod
    def get_by_id(session: Session, categoria_id: int) -> Optional[Categoria]:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.categorias.get_by_id(categoria_id)

    @staticmethod
    def get_root_categories(session: Session) -> List[Categoria]:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.categorias.get_root_categories()

    @staticmethod
    def create(session: Session, data: CategoriaCreate) -> Categoria:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_categoria = Categoria(**data.model_dump())
            uow.categorias.add(db_categoria)
            uow.commit()
            uow.categorias.refresh(db_categoria)
            return db_categoria

    @staticmethod
    def update(session: Session, categoria_id: int, data: CategoriaUpdate) -> Optional[Categoria]:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_categoria = uow.categorias.get_by_id(categoria_id)
            if not db_categoria:
                return None

            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(db_categoria, key, value)

            uow.categorias.add(db_categoria)
            uow.commit()
            uow.categorias.refresh(db_categoria)
            return db_categoria

    @staticmethod
    def soft_delete(session: Session, categoria_id: int) -> Optional[Categoria]:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_categoria = uow.categorias.get_by_id(categoria_id)
            if not db_categoria:
                return None

            db_categoria.deleted_at = get_utc_now()
            uow.categorias.add(db_categoria)
            uow.commit()
            return db_categoria