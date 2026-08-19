"""
Unit of Work for the CatalogoDeProductos module.

Provides a transactional boundary around product, category, and ingredient operations.
All repositories are accessible as attributes (uow.productos, uow.categorias, uow.ingredientes).
"""
from sqlmodel import Session
from app.core.base_uow import BaseUnitOfWork

from .Categoria.repository import CategoriaRepository
from .HistorialStock.repository import HistorialStockRepository
from .Ingrediente.repository import IngredienteRepository
from .Producto.repository import ProductoRepository
from .UnidadMedida.repository import UnidadMedidaRepository


class CatalogoDeProductosUnitOfWork(BaseUnitOfWork):
    """Unit of Work for the Catalog module.

    Usage:
        with CatalogoDeProductosUnitOfWork(session) as uow:
            uow.productos.add(...)
            uow.categorias.add(...)
            uow.commit()
    """

    def __init__(self, session: Session):
        super().__init__(session)
        self.productos = ProductoRepository(session)
        self.categorias = CategoriaRepository(session)
        self.ingredientes = IngredienteRepository(session)
        self.unidades_medida = UnidadMedidaRepository(session)
        self.historial_stock = HistorialStockRepository(session)
