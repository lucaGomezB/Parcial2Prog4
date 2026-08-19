"""
Producto repository — data access layer for Product and its many-to-many relations.

Extends BaseRepository with custom queries for managing the link tables
ProductoCategoria and ProductoIngrediente, plus batch ingredient checks
and price-recalculation support.
"""
from decimal import Decimal
from sqlmodel import Session, col, select
from sqlalchemy import case
from typing import List, Optional, Set, Tuple

from app.core.base_repository import BaseRepository
from ..producto_categoria import ProductoCategoria
from ..producto_ingrediente import ProductoIngrediente
from ..Ingrediente.models import Ingrediente
from ..Categoria.models import Categoria
from ..UnidadMedida.models import UnidadMedida
from ..utils import convertir_cantidad, load_conversion_factors
from .models import Producto


class ProductoRepository(BaseRepository[Producto]):
    """Repository for Product entity with link-table management methods."""

    def __init__(self, session: Session):
        super().__init__(session, Producto)

    def add_categoria_relacion(self, producto_id: int, categoria_id: int, es_principal: bool):
        """Create a ProductoCategoria link row."""
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
        cantidad: Decimal = Decimal("1"),
        unidad_medida_id: Optional[int] = None,
    ):
        """Create a ProductoIngrediente link row with relationship metadata."""
        enlace = ProductoIngrediente(
            producto_id=producto_id,
            ingrediente_id=ingrediente_id,
            es_removible=es_removible,
            es_principal=es_principal,
            orden=orden,
            cantidad=cantidad,
            unidad_medida_id=unidad_medida_id,
        )
        self.session.add(enlace)
        return enlace

    def get_ingredientes(self, producto_id: int):
        """Return ingredients for a product JOINed with Ingrediente and UnidadMedida.

        Uses a three-table join: inner join on Ingrediente (always present),
        left outer join on UnidadMedida (optional — ingredient might not have
        a unit assigned). Results are ordered by the 'orden' display field.
        """
        statement = (
            select(ProductoIngrediente, Ingrediente, UnidadMedida)
            .join(Ingrediente, ProductoIngrediente.ingrediente_id == Ingrediente.id)
            .outerjoin(UnidadMedida, ProductoIngrediente.unidad_medida_id == UnidadMedida.id)
            .where(ProductoIngrediente.producto_id == producto_id)
            .order_by(ProductoIngrediente.orden)
        )
        results = self.session.exec(statement).all()
        return [
            {
                "ingrediente_id": rel.ingrediente_id,
                "ingrediente_nombre": ing.nombre,
                "cantidad": rel.cantidad,
                "es_removible": rel.es_removible,
                "es_principal": rel.es_principal,
                "orden": rel.orden,
                "es_alergeno": ing.es_alergeno,
                "unidad_medida_id": rel.unidad_medida_id,
                "unidad_medida_simbolo": um.simbolo if um else None,
            }
            for rel, ing, um in results
        ]

    def get_categorias(self, producto_id: int):
        """Return categories for a product JOINed with Categoria data."""
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
        """Remove an ingredient association. Returns True if a row was deleted."""
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
        """Remove a category association. Returns True if a row was deleted."""
        statement = select(ProductoCategoria).where(
            ProductoCategoria.producto_id == producto_id,
            ProductoCategoria.categoria_id == categoria_id,
        )
        enlace = self.session.exec(statement).first()
        if enlace:
            self.session.delete(enlace)
            return True
        return False

    # ------------------------------------------------------------------
    # Query methods for service migration
    # ------------------------------------------------------------------

    def get_by_id(self, entity_id, for_update: bool = False) -> Optional[Producto]:
        """Fetch a product by ID (overrides BaseRepository to use Producto-specific PK)."""
        return super().get_by_id(entity_id, for_update=for_update)

    def get_with_ingredients(self, producto_id: int, for_update: bool = False) -> Optional[Producto]:
        """Fetch a product by ID (uses BaseRepository.get_by_id with soft-delete filter).

        When for_update=True, the row is locked with SELECT FOR UPDATE to
        prevent race conditions during stock modifications.
        """
        return self.get_by_id(producto_id, for_update=for_update)

    def get_by_ids(self, producto_ids: List[int]) -> List[Producto]:
        """Fetch multiple products by their IDs in a single query.
        Non-deleted products only. Returns empty list if no IDs provided.
        """
        if not producto_ids:
            return []
        statement = select(Producto).where(
            Producto.id.in_(producto_ids),
            Producto.deleted_at.is_(None),
        )
        return self.session.exec(statement).all()

    def get_all_with_ingredient_flag(self, skip: int = 0, limit: int = 100, search: Optional[str] = None, categoria_ids: Optional[List[int]] = None, sort_by: Optional[str] = None, sort_order: Optional[str] = None) -> Tuple[List[Producto], Set[int]]:
        """Return paginated non-deleted products and the set of IDs that have ingredients.

        Optionally filters by name ILIKE when search is provided and/or by category IDs.
        Returns (products, ids_with_ingredients) so the caller can set
        the tiene_ingredientes flag per product.
        """
        productos = self.get_all_filtered(skip=skip, limit=limit, search=search, categoria_ids=categoria_ids, sort_by=sort_by, sort_order=sort_order)
        if not productos:
            return [], set()

        product_ids = [p.id for p in productos]
        stmt = select(ProductoIngrediente.producto_id).where(
            ProductoIngrediente.producto_id.in_(product_ids)
        ).distinct()
        rows = self.session.exec(stmt).all()
        ids_with_ingredients = set(rows)
        return list(productos), ids_with_ingredients

    def get_all_filtered(self, skip: int = 0, limit: int = 100, search: Optional[str] = None, categoria_ids: Optional[List[int]] = None, sort_by: Optional[str] = None, sort_order: Optional[str] = None) -> List[Producto]:
        """List non-deleted products with optional filters and dynamic sort.
        
        Allowed sort_by values: id, nombre, precio_actual, stock_cantidad,
        tiempo_prep_min, disponible, es_producto_terminado.
        Defaults to id desc when sort_by is not provided or invalid.
        """
        ALLOWED_SORT_FIELDS = {
            "id", "nombre", "precio_actual", "stock_cantidad",
            "tiempo_prep_min", "disponible", "es_producto_terminado",
        }

        # Build base query with soft-delete filter
        stmt = select(Producto).where(Producto.deleted_at.is_(None))

        # Category filter (with descendant expansion handled by caller)
        if categoria_ids:
            matching_subq = (
                select(ProductoCategoria.producto_id)
                .where(ProductoCategoria.categoria_id.in_(categoria_ids))
            ).distinct().subquery()
            stmt = stmt.where(Producto.id.in_(select(matching_subq)))

        # Text search
        if search:
            stmt = stmt.where(Producto.nombre.ilike(f"%{search}%"))

        # Dynamic sort (with id desc as tiebreaker for deterministic ordering)
        if sort_by and sort_by in ALLOWED_SORT_FIELDS:
            if sort_by == "disponible":
                # Effective availability: considers both the toggle AND stock level.
                # Products with stock_cantidad <= 0 are treated as unavailable
                # regardless of the disponible flag, matching the frontend display.
                effective = case(
                    ((Producto.disponible == False) | (Producto.stock_cantidad <= 0), 0),
                    else_=1,
                )
                stmt = stmt.order_by(
                    effective.desc() if sort_order == "desc" else effective.asc(),
                    Producto.id.desc(),
                )
            elif sort_by == "id":
                sort_col = getattr(Producto, sort_by)
                stmt = stmt.order_by(
                    sort_col.desc() if sort_order == "desc" else sort_col.asc()
                )
            else:
                sort_col = getattr(Producto, sort_by)
                stmt = stmt.order_by(
                    sort_col.desc() if sort_order == "desc" else sort_col.asc(),
                    Producto.id.desc(),
                )
        else:
            stmt = stmt.order_by(Producto.id.desc())

        # Pagination
        stmt = stmt.offset(skip).limit(limit)

        return self.session.exec(stmt).all()

    def get_productos_afectados(self, ingrediente_id: int) -> List[int]:
        """Return distinct product IDs that use a given ingredient."""
        statement = select(ProductoIngrediente.producto_id).where(
            ProductoIngrediente.ingrediente_id == ingrediente_id,
        ).distinct()
        return self.session.exec(statement).all()

    def get_producto_ingredientes(self, producto_id: int):
        """Return all ProductoIngrediente associations for a product."""
        statement = select(ProductoIngrediente).where(
            ProductoIngrediente.producto_id == producto_id,
        )
        return self.session.exec(statement).all()

    def get_producto_ingrediente(self, producto_id: int, ingrediente_id: int):
        """Return a specific ProductoIngrediente association (or None)."""
        statement = select(ProductoIngrediente).where(
            ProductoIngrediente.producto_id == producto_id,
            ProductoIngrediente.ingrediente_id == ingrediente_id,
        )
        return self.session.exec(statement).first()

    def get_ingrediente(self, ingrediente_id: int) -> Optional[Ingrediente]:
        """Fetch a single ingredient by ID."""
        return self.session.get(Ingrediente, ingrediente_id)

    def get_producto_terminado_ids(self, producto_ids: List[int]) -> Set[int]:
        """Return the subset of product IDs that are productos terminados."""
        if not producto_ids:
            return set()
        statement = select(Producto.id).where(
            Producto.id.in_(producto_ids),
            Producto.es_producto_terminado == True,
        )
        return set(self.session.exec(statement).all())

    # ------------------------------------------------------------------
    # Derived stock computation (Phase 1: additive, non-breaking)
    # See docs/openspec/changes/make-to-order-migration for full context.
    # ------------------------------------------------------------------

    def compute_derived_stock(self, producto_id: int) -> int:
        """Compute product stock from ingredient availability.

        Formula: min(floor(ing.stock_actual / converted_per_unit_qty))
        across all ProductoIngrediente rows for this product.
        A product with no ingredients returns 0.

        This is the individual (non-batch) variant. For listings,
        prefer compute_derived_stock_batch to avoid N+1 queries.
        """
        from ..producto_ingrediente import ProductoIngrediente as PI
        associations = self.session.exec(
            select(PI, Ingrediente)
            .join(Ingrediente, PI.ingrediente_id == Ingrediente.id)
            .where(PI.producto_id == producto_id)
        ).all()

        if not associations:
            return 0

        factores = load_conversion_factors(self.session)
        min_stock: Optional[int] = None
        for pi, ing in associations:
            converted = convertir_cantidad(
                Decimal(pi.cantidad),
                pi.unidad_medida_id,
                ing.unidad_medida_id,
                factores=factores,
            )
            producible = int(ing.stock_actual // converted) if converted > 0 else 0
            if min_stock is None or producible < min_stock:
                min_stock = producible
        return min_stock or 0

    def get_ingredientes_stock_detail(self, producto_id: int) -> list[dict]:
        """Return per-ingredient stock breakdown for a product.

        For each ingredient, computes: how many units it can produce,
        whether it is the limiting factor, and the deficit needed to
        reach at least 1 producible unit.

        Returns an empty list for products with no ingredients or when
        the product does not exist.
        """
        from ..producto_ingrediente import ProductoIngrediente as PI
        associations = self.session.exec(
            select(PI, Ingrediente, UnidadMedida)
            .join(Ingrediente, PI.ingrediente_id == Ingrediente.id)
            .outerjoin(UnidadMedida, Ingrediente.unidad_medida_id == UnidadMedida.id)
            .where(PI.producto_id == producto_id)
        ).all()

        if not associations:
            return []

        factores = load_conversion_factors(self.session)

        # First pass: compute producible per ingredient, find the minimum
        details: list[dict] = []
        min_producible: int | None = None
        for pi, ing, um in associations:
            converted = convertir_cantidad(
                Decimal(pi.cantidad),
                pi.unidad_medida_id,
                ing.unidad_medida_id,
                factores=factores,
            )
            producible = int(ing.stock_actual // converted) if converted > 0 else 0
            deficit = max(0, int(converted) - ing.stock_actual) if producible == 0 else 0
            details.append({
                "ingrediente_id": ing.id,
                "ingrediente_nombre": ing.nombre,
                "stock_actual": ing.stock_actual,
                "cantidad_receta": Decimal(pi.cantidad),
                "cantidad_convertida": converted,
                "unidad_medida_simbolo": um.simbolo if um else None,
                "producible": producible,
                "deficit": deficit,
            })
            if min_producible is None or producible < min_producible:
                min_producible = producible

        # Second pass: mark limiting ingredients
        if min_producible is not None:
            for d in details:
                d["es_limitante"] = d["producible"] == min_producible

        return details

    def compute_derived_stock_batch(self, producto_ids: List[int]) -> dict[int, int]:
        """Batch compute derived stock for multiple product IDs.

        Uses a single query joining producto_ingrediente + ingrediente,
        computing MIN(floor(stock_actual / converted)) grouped by producto_id.
        Returns {producto_id: derived_stock}. Products with no ingredients
        are NOT included in the result (caller treats missing key as 0).
        """
        if not producto_ids:
            return {}

        from ..producto_ingrediente import ProductoIngrediente as PI

        # Load all associations for the requested products in one query
        associations = self.session.exec(
            select(PI, Ingrediente)
            .join(Ingrediente, PI.ingrediente_id == Ingrediente.id)
            .where(PI.producto_id.in_(producto_ids))
        ).all()

        if not associations:
            return {}

        factores = load_conversion_factors(self.session)

        # Group by producto_id and compute min derivable units
        result: dict[int, Optional[int]] = {}
        for pi, ing in associations:
            converted = convertir_cantidad(
                Decimal(pi.cantidad),
                pi.unidad_medida_id,
                ing.unidad_medida_id,
                factores=factores,
            )
            producible = int(ing.stock_actual // converted) if converted > 0 else 0
            pid = pi.producto_id
            if pid not in result:
                result[pid] = producible
            elif producible < (result[pid] or 0):
                result[pid] = producible

        return {pid: val or 0 for pid, val in result.items()}

    def get_productos_afectados_por_ingrediente(self, ingrediente_id: int) -> List[int]:
        """Return distinct active product IDs that reference this ingredient.

        Includes only non-deleted products. Used to trigger derived stock
        recomputation when an ingredient's stock changes.
        """
        from ..producto_ingrediente import ProductoIngrediente as PI
        statement = (
            select(PI.producto_id)
            .join(Producto, PI.producto_id == Producto.id)
            .where(
                PI.ingrediente_id == ingrediente_id,
                Producto.deleted_at.is_(None),
            )
            .distinct()
        )
        return self.session.exec(statement).all()

    def get_ingredientes_compartidos(self) -> dict[int, list[str]]:
        """Return {producto_id: [shared ingredient names]}.

        An ingredient is "shared" when 2 or more active products use it.
        Only non-deleted products and ingredients are considered.
        """
        stmt = (
            select(ProductoIngrediente.producto_id, ProductoIngrediente.ingrediente_id, Ingrediente.nombre)
            .join(Ingrediente, ProductoIngrediente.ingrediente_id == Ingrediente.id)
            .join(Producto, ProductoIngrediente.producto_id == Producto.id)
            .where(
                Producto.deleted_at.is_(None),
                Ingrediente.deleted_at.is_(None),
            )
        )
        rows = self.session.exec(stmt).all()

        productos_por_ing: dict[int, set[int]] = {}
        nombre_ing: dict[int, str] = {}
        ing_por_producto: dict[int, list[int]] = {}
        for producto_id, ingrediente_id, nombre in rows:
            productos_por_ing.setdefault(ingrediente_id, set()).add(producto_id)
            nombre_ing[ingrediente_id] = nombre
            ing_por_producto.setdefault(producto_id, []).append(ingrediente_id)

        result: dict[int, list[str]] = {}
        for producto_id, ing_ids in ing_por_producto.items():
            compartidos = sorted(
                nombre_ing[iid] for iid in ing_ids if len(productos_por_ing[iid]) >= 2
            )
            if compartidos:
                result[producto_id] = compartidos
        return result

    def count_all(self, search: Optional[str] = None, categoria_ids: Optional[List[int]] = None) -> int:
        """Count all non-deleted products, optionally filtered by name search and/or category IDs."""
        from sqlmodel import func
        if categoria_ids:
            matching_subq = (
                select(ProductoCategoria.producto_id)
                .where(ProductoCategoria.categoria_id.in_(categoria_ids))
            ).distinct().subquery()
            stmt = select(func.count()).select_from(Producto).where(
                Producto.deleted_at.is_(None),
                Producto.id.in_(select(matching_subq)),
            )
            if search:
                stmt = stmt.where(Producto.nombre.ilike(f"%{search}%"))
            return self.session.exec(stmt).one()
        return super().count_all(search=search, search_column="nombre" if search else None)
