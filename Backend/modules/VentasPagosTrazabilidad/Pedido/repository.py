"""
Pedido repository — data access layer for Order.

Extends BaseRepository with eager-loading, state-filtered queries,
and cross-module lookups for stock validation (Producto, Ingrediente).
"""
from sqlmodel import Session, select, col
from typing import List, Optional
from sqlalchemy.orm import selectinload
from models.base_repository import BaseRepository
from .models import Pedido
from ..DetallePedido.models import DetallePedido

ESTADOS_TERMINALES = {"ENTREGADO", "CANCELADO"}


class PedidoRepository(BaseRepository[Pedido]):
    """Repository for Pedido with eager-loading and state-filtered queries."""

    def __init__(self, session: Session):
        super().__init__(session, Pedido)

    def get_by_usuario_id(self, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Return non-deleted orders for a given user, newest first."""
        statement = (
            select(Pedido)
            .where(Pedido.usuario_id == usuario_id, col(Pedido.deleted_at).is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.id.desc())
        )
        return self.session.exec(statement).all()

    # ------------------------------------------------------------------
    # Eager-loading helpers
    # ------------------------------------------------------------------

    def _eager_options(self):
        """Return selectinload options for eager-loading Pedido relationships."""
        return [
            selectinload(Pedido.detalles),
            selectinload(Pedido.estado),
            selectinload(Pedido.usuario),
            selectinload(Pedido.direccion),
            selectinload(Pedido.forma_pago),
        ]

    # ------------------------------------------------------------------
    # Eager-loaded read methods
    # ------------------------------------------------------------------

    def get_all_eager(self, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """List all orders with eager-loaded relationships, paginated."""
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.id.desc())
        )
        return self.session.exec(statement).all()

    def get_by_id_eager(self, pedido_id: int) -> Optional[Pedido]:
        """Fetch a single order by ID with eager-loaded relationships."""
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .where(Pedido.id == pedido_id)
        )
        return self.session.exec(statement).first()

    def get_by_usuario_id_eager(self, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Fetch non-deleted orders for a specific user with eager-loaded relationships."""
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .where(Pedido.usuario_id == usuario_id, col(Pedido.deleted_at).is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_activos(self, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Fetch non-terminal orders (not ENTREGADO or CANCELADO), newest first."""
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .where(col(Pedido.estado_codigo).not_in(ESTADOS_TERMINALES))
            .where(col(Pedido.deleted_at).is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.created_at.desc())
        )
        return self.session.exec(statement).all()

    def get_historial(self, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Fetch terminal-state orders (ENTREGADO or CANCELADO), most recently updated first."""
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .where(col(Pedido.estado_codigo).in_(ESTADOS_TERMINALES))
            .where(col(Pedido.deleted_at).is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.updated_at.desc())
        )
        return self.session.exec(statement).all()

    def get_historial_by_usuario(self, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Fetch terminal-state orders for a specific user."""
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .where(Pedido.usuario_id == usuario_id)
            .where(col(Pedido.estado_codigo).in_(ESTADOS_TERMINALES))
            .where(col(Pedido.deleted_at).is_(None))
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.updated_at.desc())
        )
        return self.session.exec(statement).all()

    # ------------------------------------------------------------------
    # DetallePedido queries
    # ------------------------------------------------------------------

    def get_detalles(self, pedido_id: int) -> List[DetallePedido]:
        """Return all detail lines for an order."""
        statement = select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)
        return self.session.exec(statement).all()

    def get_detalle_by_producto(self, pedido_id: int, producto_id: int) -> Optional[DetallePedido]:
        """Return a specific detail line by product within an order."""
        statement = select(DetallePedido).where(
            DetallePedido.pedido_id == pedido_id,
            DetallePedido.producto_id == producto_id,
        )
        return self.session.exec(statement).first()

    # ------------------------------------------------------------------
    # Cross-module lookups for stock validation
    # ------------------------------------------------------------------

    def get_producto(self, producto_id: int):
        """Fetch a product by ID (cross-module, for stock validation)."""
        from modules.CatalogoDeProductos.Producto.models import Producto
        return self.session.get(Producto, producto_id)

    def get_producto_ingredientes(self, producto_id: int):
        """Fetch ProductoIngrediente associations for a product (cross-module)."""
        from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
        statement = select(ProductoIngrediente).where(
            ProductoIngrediente.producto_id == producto_id
        )
        return self.session.exec(statement).all()

    def get_ingrediente(self, ingrediente_id: int):
        """Fetch a single ingredient by ID (cross-module)."""
        from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
        return self.session.get(Ingrediente, ingrediente_id)

    # ------------------------------------------------------------------
    # Count methods
    # ------------------------------------------------------------------

    def count_all(self) -> int:
        """Count all non-deleted orders."""
        from sqlmodel import func
        from sqlalchemy import column
        statement = select(func.count()).select_from(self.model_class)
        statement = statement.where(column("deleted_at").is_(None))
        result = self.session.exec(statement)
        return result.one()

    def count_activos(self) -> int:
        """Count non-terminal (not ENTREGADO or CANCELADO) non-deleted orders."""
        from sqlmodel import func
        from sqlalchemy import column
        statement = select(func.count()).select_from(self.model_class)
        statement = statement.where(
            column("estado_codigo").not_in(ESTADOS_TERMINALES),
            column("deleted_at").is_(None),
        )
        result = self.session.exec(statement)
        return result.one()

    def count_historial(self) -> int:
        """Count terminal-state (ENTREGADO or CANCELADO) non-deleted orders."""
        from sqlmodel import func
        from sqlalchemy import column
        statement = select(func.count()).select_from(self.model_class)
        statement = statement.where(
            column("estado_codigo").in_(ESTADOS_TERMINALES),
            column("deleted_at").is_(None),
        )
        result = self.session.exec(statement)
        return result.one()

    def count_by_usuario_id(self, usuario_id: int) -> int:
        """Count non-deleted orders for a given user."""
        from sqlmodel import func
        from sqlalchemy import column
        statement = select(func.count()).select_from(self.model_class)
        statement = statement.where(
            column("usuario_id") == usuario_id,
            column("deleted_at").is_(None),
        )
        result = self.session.exec(statement)
        return result.one()
