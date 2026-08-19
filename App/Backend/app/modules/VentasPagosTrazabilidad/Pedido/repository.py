"""
Pedido repository — data access layer for Order.

Extends BaseRepository with eager-loading, state-filtered queries,
and cross-module lookups for stock validation (Producto, Ingrediente).
"""
from sqlmodel import Session, select, col, asc, desc
from typing import List, Optional
from sqlalchemy.orm import selectinload
from sqlalchemy import or_, cast, String
from app.core.base_repository import BaseRepository
from app.modules.IdentidadYAcceso.Usuario.models import Usuario
from .models import Pedido
from ..DetallePedido.models import DetallePedido

ESTADOS_TERMINALES = {"ENTREGADO", "CANCELADO"}

SORTABLE_FIELDS = {"id", "estado_codigo", "created_at", "updated_at", "total"}

def _apply_sort(statement, model, sort_by: str = "id", sort_order: str = "desc"):
    """Apply dynamic ordering to a SQLModel select statement."""
    column = getattr(model, sort_by, model.id)
    direction = asc(column) if sort_order == "asc" else desc(column)
    return statement.order_by(direction)


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
        """List all non-deleted orders with eager-loaded relationships, paginated."""
        statement = (
            select(Pedido)
            .where(col(Pedido.deleted_at).is_(None))
            .options(*self._eager_options())
            .offset(skip)
            .limit(limit)
            .order_by(Pedido.id.desc())
        )
        return self.session.exec(statement).all()

    def get_by_id_eager(self, pedido_id: int) -> Optional[Pedido]:
        """Fetch a single non-deleted order by ID with eager-loaded relationships."""
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .where(Pedido.id == pedido_id, col(Pedido.deleted_at).is_(None))
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

    def get_activos(self, skip: int = 0, limit: int = 100, sort_by: str = "id", sort_order: str = "desc", search: Optional[str] = None) -> List[Pedido]:
        """Fetch non-terminal orders (not ENTREGADO or CANCELADO), with dynamic sorting and optional text search.

        When `search` is provided, filters by ILIKE on:
          - Pedido.id (cast to text) — match by order number
          - Usuario.email — match by customer email (via join)
          - Usuario.nombre — match by customer name (via join)
          - Pedido.notas — match by order notes
        """
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .where(col(Pedido.estado_codigo).not_in(ESTADOS_TERMINALES))
            .where(col(Pedido.deleted_at).is_(None))
        )
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.join(Pedido.usuario).where(
                or_(
                    cast(Pedido.id, String).ilike(pattern),
                    Usuario.email.ilike(pattern),
                    Usuario.nombre.ilike(pattern),
                    Pedido.notas.ilike(pattern),
                )
            )
        statement = statement.offset(skip).limit(limit)
        statement = _apply_sort(statement, Pedido, sort_by, sort_order)
        return self.session.exec(statement).all()

    def get_historial(self, skip: int = 0, limit: int = 100, sort_by: str = "id", sort_order: str = "desc", search: Optional[str] = None) -> List[Pedido]:
        """Fetch terminal-state orders (ENTREGADO or CANCELADO), with dynamic sorting and optional text search.

        When `search` is provided, filters by ILIKE on Pedido.id (cast to text),
        Usuario.email, Usuario.nombre (via join), and Pedido.notas.
        """
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .where(col(Pedido.estado_codigo).in_(ESTADOS_TERMINALES))
            .where(col(Pedido.deleted_at).is_(None))
        )
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.join(Pedido.usuario).where(
                or_(
                    cast(Pedido.id, String).ilike(pattern),
                    Usuario.email.ilike(pattern),
                    Usuario.nombre.ilike(pattern),
                    Pedido.notas.ilike(pattern),
                )
            )
        statement = statement.offset(skip).limit(limit)
        statement = _apply_sort(statement, Pedido, sort_by, sort_order)
        return self.session.exec(statement).all()

    def get_historial_by_usuario(self, usuario_id: int, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> List[Pedido]:
        """Fetch terminal-state orders for a specific user, with optional text search."""
        statement = (
            select(Pedido)
            .options(*self._eager_options())
            .where(Pedido.usuario_id == usuario_id)
            .where(col(Pedido.estado_codigo).in_(ESTADOS_TERMINALES))
            .where(col(Pedido.deleted_at).is_(None))
        )
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    cast(Pedido.id, String).ilike(pattern),
                    Pedido.notas.ilike(pattern),
                )
            )
        statement = statement.offset(skip).limit(limit).order_by(Pedido.updated_at.desc())
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

    def get_producto(self, producto_id: int, for_update: bool = False):
        """Fetch a product by ID (cross-module, for stock validation).

        When for_update=True, the row is locked with SELECT FOR UPDATE to
        prevent race conditions during stock deduction in order confirmation.
        """
        from app.modules.CatalogoDeProductos.Producto.models import Producto
        if for_update:
            from sqlmodel import select as sql_select
            stmt = sql_select(Producto).where(Producto.id == producto_id).with_for_update()
            return self.session.exec(stmt).first()
        return self.session.get(Producto, producto_id)

    def get_producto_ingredientes(self, producto_id: int):
        """Fetch ProductoIngrediente associations for a product (cross-module)."""
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
        statement = select(ProductoIngrediente).where(
            ProductoIngrediente.producto_id == producto_id
        )
        return self.session.exec(statement).all()

    def get_ingrediente(self, ingrediente_id: int):
        """Fetch a single ingredient by ID (cross-module)."""
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente
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

    def count_activos(self, search: Optional[str] = None) -> int:
        """Count non-terminal (not ENTREGADO or CANCELADO) non-deleted orders, with optional text search."""
        from sqlmodel import func
        from sqlalchemy import column
        statement = select(func.count()).select_from(self.model_class)
        statement = statement.where(
            column("estado_codigo").not_in(ESTADOS_TERMINALES),
            column("deleted_at").is_(None),
        )
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.join(Usuario, Pedido.usuario_id == Usuario.id).where(
                or_(
                    cast(Pedido.id, String).ilike(pattern),
                    Usuario.email.ilike(pattern),
                    Usuario.nombre.ilike(pattern),
                    column("notas").ilike(pattern),
                )
            )
        result = self.session.exec(statement)
        return result.one()

    def count_historial(self, search: Optional[str] = None) -> int:
        """Count terminal-state (ENTREGADO or CANCELADO) non-deleted orders, with optional text search."""
        from sqlmodel import func
        from sqlalchemy import column
        statement = select(func.count()).select_from(self.model_class)
        statement = statement.where(
            column("estado_codigo").in_(ESTADOS_TERMINALES),
            column("deleted_at").is_(None),
        )
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.join(Usuario, Pedido.usuario_id == Usuario.id).where(
                or_(
                    cast(Pedido.id, String).ilike(pattern),
                    Usuario.email.ilike(pattern),
                    Usuario.nombre.ilike(pattern),
                    column("notas").ilike(pattern),
                )
            )
        result = self.session.exec(statement)
        return result.one()

    def count_by_usuario_id(self, usuario_id: int, search: Optional[str] = None) -> int:
        """Count non-deleted orders for a given user, with optional text search."""
        from sqlmodel import func
        from sqlalchemy import column
        statement = select(func.count()).select_from(self.model_class)
        statement = statement.where(
            column("usuario_id") == usuario_id,
            column("deleted_at").is_(None),
        )
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    cast(Pedido.id, String).ilike(pattern),
                    column("notas").ilike(pattern),
                )
            )
        result = self.session.exec(statement)
        return result.one()

    # ------------------------------------------------------------------
    # Phase 2: Ingredient-level stock operations (make-to-order)
    # ------------------------------------------------------------------

    def get_producto_with_ingredients(self, producto_id: int):
        """Return ProductoIngrediente + Ingrediente tuples for a product.

        Loads both the association (cantidad, unidad_medida_id) and the
        ingredient (stock_actual, unidad_medida_id) in a single JOIN query.

        Returns list of (ProductoIngrediente, Ingrediente) tuples.
        Empty list if the product has no ingredient associations.
        """
        from app.modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente as PI
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente

        statement = (
            select(PI, Ingrediente)
            .join(Ingrediente, PI.ingrediente_id == Ingrediente.id)
            .where(PI.producto_id == producto_id)
        )
        return self.session.exec(statement).all()

    def lock_ingredients_for_order(self, ingredient_ids: list[int]):
        """Lock ingredient rows with SELECT FOR UPDATE, ordered by ID ASC.

        Ordering by ID ASC prevents deadlocks when two concurrent orders
        contain different products that share ingredients.

        Returns list of locked Ingrediente ORM instances.
        """
        from app.modules.CatalogoDeProductos.Ingrediente.models import Ingrediente

        if not ingredient_ids:
            return []

        statement = (
            select(Ingrediente)
            .where(Ingrediente.id.in_(ingredient_ids))
            .order_by(Ingrediente.id.asc())
            .with_for_update()
        )
        return self.session.exec(statement).all()
