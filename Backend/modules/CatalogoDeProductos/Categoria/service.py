from typing import List, Optional
from fastapi import HTTPException, status
from sqlmodel import Session, col, select
from .models import Categoria
from .schemas import CategoriaCreate, CategoriaUpdate
from models.base import get_utc_now
from ..uow import CatalogoDeProductosUnitOfWork
from ..Producto.models import Producto
from ..producto_categoria import ProductoCategoria


class CategoriaService:
    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100, parent_id: int | None = None) -> List[Categoria]:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.categorias.get_all(skip=skip, limit=limit, parent_id=parent_id)

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
        # Validar que el nombre no exista ya (unique constraint)
        existing = session.exec(
            select(Categoria).where(Categoria.nombre == data.nombre, Categoria.deleted_at.is_(None))
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Ya existe una categoría con el nombre '{data.nombre}'"
            )

        # Validar que el parent_id exista (FK constraint)
        if data.parent_id is not None:
            parent = session.exec(
                select(Categoria).where(Categoria.id == data.parent_id, Categoria.deleted_at.is_(None))
            ).first()
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="La categoría padre indicada no existe"
                )

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

            # Validate no active products are linked to this category
            stmt = (
                select(ProductoCategoria)
                .join(Producto, ProductoCategoria.producto_id == Producto.id)
                .where(
                    ProductoCategoria.categoria_id == categoria_id,
                    col(Producto.deleted_at).is_(None)
                )
                .limit(1)
            )
            active_link = uow.session.exec(stmt).first()
            if active_link:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede eliminar la categoría: tiene productos activos asociados"
                )

            db_categoria.deleted_at = get_utc_now()
            uow.categorias.add(db_categoria)
            uow.commit()
            return db_categoria