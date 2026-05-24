from sqlmodel import Session

from .Categoria.repository import CategoriaRepository
from .Ingrediente.repository import IngredienteRepository
from .Producto.repository import ProductoRepository


class CatalogoDeProductosUnitOfWork:
    def __init__(self, session: Session):
        self.session = session
        self.productos = ProductoRepository(session)
        self.categorias = CategoriaRepository(session)
        self.ingredientes = IngredienteRepository(session)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        return False

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
