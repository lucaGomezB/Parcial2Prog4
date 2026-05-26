from sqlmodel import Session, col, select

from models.base_repository import BaseRepository
from ..producto_categoria import ProductoCategoria
from ..producto_ingrediente import ProductoIngrediente
from ..Ingrediente.models import Ingrediente
from ..Categoria.models import Categoria
from .models import Producto


class ProductoRepository(BaseRepository[Producto]):
    def __init__(self, session: Session):
        super().__init__(session, Producto)

    def add_categoria_relacion(self, producto_id: int, categoria_id: int, es_principal: bool):
        enlace = ProductoCategoria(
            producto_id=producto_id,
            categoria_id=categoria_id,
            es_principal=es_principal,
        )
        self.session.add(enlace)
        return enlace

    def add_ingrediente_relacion(
        self,
        producto_id: int,
        ingrediente_id: int,
        es_removible: bool,
        es_principal: bool,
        orden: int = 0,
    ):
        enlace = ProductoIngrediente(
            producto_id=producto_id,
            ingrediente_id=ingrediente_id,
            es_removible=es_removible,
            es_principal=es_principal,
            orden=orden,
        )
        self.session.add(enlace)
        return enlace

    def get_ingredientes(self, producto_id: int):
        """Devuelve los ingredientes asociados a un producto con datos de la relación."""
        statement = (
            select(ProductoIngrediente, Ingrediente)
            .join(Ingrediente, ProductoIngrediente.ingrediente_id == Ingrediente.id)
            .where(ProductoIngrediente.producto_id == producto_id)
            .order_by(ProductoIngrediente.orden)
        )
        results = self.session.exec(statement).all()
        return [
            {
                "ingrediente_id": rel.ingrediente_id,
                "ingrediente_nombre": ing.nombre,
                "es_removible": rel.es_removible,
                "es_principal": rel.es_principal,
                "orden": rel.orden,
            }
            for rel, ing in results
        ]

    def get_categorias(self, producto_id: int):
        """Devuelve las categorías asociadas a un producto."""
        statement = (
            select(ProductoCategoria, Categoria)
            .join(Categoria, ProductoCategoria.categoria_id == Categoria.id)
            .where(ProductoCategoria.producto_id == producto_id)
        )
        results = self.session.exec(statement).all()
        return [
            {
                "categoria_id": rel.categoria_id,
                "categoria_nombre": cat.nombre,
                "es_principal": rel.es_principal,
            }
            for rel, cat in results
        ]

    def delete_ingrediente_relacion(self, producto_id: int, ingrediente_id: int):
        """Elimina la relación entre un producto y un ingrediente."""
        statement = select(ProductoIngrediente).where(
            ProductoIngrediente.producto_id == producto_id,
            ProductoIngrediente.ingrediente_id == ingrediente_id,
        )
        enlace = self.session.exec(statement).first()
        if enlace:
            self.session.delete(enlace)
            return True
        return False

    def delete_categoria_relacion(self, producto_id: int, categoria_id: int):
        """Elimina la relación entre un producto y una categoría."""
        statement = select(ProductoCategoria).where(
            ProductoCategoria.producto_id == producto_id,
            ProductoCategoria.categoria_id == categoria_id,
        )
        enlace = self.session.exec(statement).first()
        if enlace:
            self.session.delete(enlace)
            return True
        return False
