"""
Producto service — business logic for product CRUD, ingredient/category
management, and automatic price recalculation.

This is the thickest layer in the Product module. Key invariants:
- precio_base is auto-calculated from ingredient costs when ingredients exist
- Stock transitions can trigger ingredient stock consumption
- Soft-delete is used (no physical row removal)
- All write operations use the Unit of Work pattern
"""
from decimal import Decimal

from fastapi import HTTPException
from sqlmodel import Session
from .models import Producto
from .repository import ProductoRepository
from .schemas import ProductoCreate, ProductoRead, ProductoUpdate, IngredienteAsignado, CategoriaAsignada
from models.base import get_utc_now
from ..Categoria.models import Categoria
from ..Ingrediente.models import Ingrediente
from ..producto_ingrediente import ProductoIngrediente
from ..uow import CatalogoDeProductosUnitOfWork


class ProductoService:
    """Business logic for the Product entity."""

    @staticmethod
    def create(session: Session, data: ProductoCreate):
        """Create a product with optional category and ingredient associations.

        Business rules:
        - stock_cantidad == 0 automatically sets disponible = False
        - The price is recalculated from ingredients if any are assigned
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            producto_data = data.model_dump(exclude={"categorias_ids", "categoria_principal_id", "ingredientes"})
            db_producto = Producto(**producto_data)
            # Business rule: zero stock means the product is not available for sale.
            if db_producto.stock_cantidad == 0:
                db_producto.disponible = False

            # Set precio_actual default to precio_base if not provided
            if db_producto.precio_actual is None or db_producto.precio_actual == 0:
                db_producto.precio_actual = db_producto.precio_base

            # Validate: precio_actual must not be lower than precio_base
            if db_producto.precio_actual < db_producto.precio_base:
                raise HTTPException(
                    status_code=400,
                    detail="El precio actual no puede ser menor al precio base"
                )

            # Validate price: must be > 0 when the product has no ingredients
            # and is not marked as an insumo (resold item with manual price).
            if not data.es_insumo and (not data.ingredientes) and db_producto.precio_base <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="El precio base debe ser mayor a 0 cuando el producto no tiene ingredientes ni es de reventa"
                )

            uow.productos.add(db_producto)
            uow.productos.flush()

            if data.categorias_ids:
                for cat_id in data.categorias_ids:
                    uow.productos.add_categoria_relacion(
                        producto_id=db_producto.id,
                        categoria_id=cat_id,
                        es_principal=(cat_id == data.categoria_principal_id),
                    )

            # Skip ingredient block entirely for insumo products
            if not data.es_insumo and data.ingredientes:
                for ingrediente in data.ingredientes:
                    uow.productos.add_ingrediente_relacion(
                        producto_id=db_producto.id,
                        ingrediente_id=ingrediente.ingrediente_id,
                        es_removible=ingrediente.es_removible,
                        es_principal=ingrediente.es_principal,
                        orden=ingrediente.orden,
                        cantidad=ingrediente.cantidad,
                    )

            # Recalculate price if the product has ingredients (skip for insumo)
            if not data.es_insumo and data.ingredientes:
                ProductoService._recalcular_precio_producto(session, db_producto.id)

            uow.productos.refresh(db_producto)
            return db_producto

    @staticmethod
    def _recalcular_precio_producto(session: Session, producto_id: int):
        """Recalculate precio_base = SUM(ingrediente.precio_actual * pi.cantidad).

        This method does NOT manage its own UoW — the calling method
        is responsible for the transaction boundary.
        """
        repo = ProductoRepository(session)
        db_producto = repo.get_with_ingredients(producto_id)
        if not db_producto:
            return

        # Skip recalculation for insumo products (their price is manual)
        if db_producto.es_insumo:
            return

        # Fetch all ProductoIngrediente associations for this product
        associations = repo.get_producto_ingredientes(producto_id)

        if not associations:
            return

        total = Decimal('0')
        for pi in associations:
            ing = repo.get_ingrediente(pi.ingrediente_id)
            if ing and ing.precio_actual:
                total += ing.precio_actual * Decimal(pi.cantidad)

        db_producto.precio_base = total

        # Ensure precio_actual is not lower than the recalculated precio_base
        if db_producto.precio_actual < db_producto.precio_base:
            db_producto.precio_actual = db_producto.precio_base

        session.add(db_producto)

    @staticmethod
    def recalcular_precio_productos_afectados(session: Session, ingrediente_id: int):
        """Recalculate precio_base for ALL products using a given ingredient.

        Called automatically when an ingredient's price changes.
        Manages its own UoW transaction. The UoW __exit__ handles commit.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            repo = ProductoRepository(session)
            producto_ids = repo.get_productos_afectados(ingrediente_id)

            # Exclude insumo products from recalculation (their price is manual).
            # Single batch query instead of N+1 individual session.get() calls.
            if producto_ids:
                insumo_ids = repo.get_insumo_ids(producto_ids)
                producto_ids = [pid for pid in producto_ids if pid not in insumo_ids]

            for pid in producto_ids:
                ProductoService._recalcular_precio_producto(session, pid)

            # NOTE: No manual uow.commit() — the UoW __exit__ handles it automatically.

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100):
        """List all non-deleted products with pagination and ingredient flag.

        Read-only: does NOT use UoW because commit() would expire ORM objects,
        causing FastAPI serialization errors.

        The tiene_ingredientes flag is computed in a batch query to
        avoid N+1 checks per product.
        """
        repo = ProductoRepository(session)
        productos, ids_with_ingredients = repo.get_all_with_ingredient_flag(skip=skip, limit=limit)

        if not productos:
            return productos

        # Build ProductoRead response with computed tiene_ingredientes
        result = []
        for p in productos:
            if p.imagenes_url is None:
                p.imagenes_url = []
            base = ProductoRead.model_validate(p).model_dump(exclude={"tiene_ingredientes"})
            result.append(
                ProductoRead(
                    **base,
                    tiene_ingredientes=p.id in ids_with_ingredients,
                )
            )
        return result

    @staticmethod
    def get_by_id(session: Session, producto_id: int):
        """Fetch a single non-deleted product by ID.

        Read-only: uses repository directly (no UoW).
        """
        repo = ProductoRepository(session)
        return repo.get_with_ingredients(producto_id)

    @staticmethod
    def update(session: Session, producto_id: int, data: ProductoUpdate):
        """Update a product with stock-aware business rules.

        Key business rules:
        - Increasing stock consumes ingredient stock (validates availability)
        - Changing disponible from False -> True automatically adds 1 to stock
        - Stock reaching 0 automatically flips disponible to False
        - Price is recalculated if the product has ingredients
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None

            repo = ProductoRepository(session)
            values = data.model_dump(exclude_unset=True)

            # Track state before applying changes, for transition detection
            old_stock = db_producto.stock_cantidad
            old_disponible = db_producto.disponible

            for key, value in values.items():
                setattr(db_producto, key, value)

            # If stock was increased, deduct the difference from ingredient inventory
            new_stock = db_producto.stock_cantidad
            if 'stock_cantidad' in values and new_stock > old_stock:
                diff = new_stock - old_stock
                associations = repo.get_producto_ingredientes(producto_id)

                # First pass: validate ALL ingredients, collect every shortage
                shortages: list[str] = []
                for pi in associations:
                    ing = repo.get_ingrediente(pi.ingrediente_id)
                    if ing:
                        needed = pi.cantidad * diff
                        if ing.stock_actual < needed:
                            shortages.append(
                                f"'{ing.nombre}': necesita {needed}, tiene {ing.stock_actual}"
                            )

                # If ANY ingredient is short, report ALL at once — do NOT deduct anything
                if shortages:
                    lines = "\n".join(f"  - {s}" for s in shortages)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Stock insuficiente en los siguientes ingredientes:\n{lines}"
                    )

                # Second pass: all validated — deduct now
                for pi in associations:
                    ing = repo.get_ingrediente(pi.ingrediente_id)
                    if ing:
                        needed = pi.cantidad * diff
                        ing.stock_actual -= needed
                        session.add(ing)

            # Rule: transitioning from unavailable to available adds 1 to stock
            if db_producto.disponible is True and old_disponible is False:
                db_producto.stock_cantidad = (db_producto.stock_cantidad or 0) + 1

            # Rule: zero stock forces unavailable
            if db_producto.stock_cantidad == 0:
                db_producto.disponible = False

            # Validate: if precio_actual was updated, it must not be lower than precio_base
            if 'precio_actual' in values and db_producto.precio_actual < db_producto.precio_base:
                raise HTTPException(
                    status_code=400,
                    detail="El precio actual no puede ser menor al precio base"
                )

            # Validate price after updates: must be > 0 when the product
            # has no ingredients and is not an insumo (resold item).
            if not db_producto.es_insumo and not db_producto.ingredientes and db_producto.precio_base <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="El precio base debe ser mayor a 0 cuando el producto no tiene ingredientes ni es de reventa"
                )

            # Recalculate price if the product has ingredients (skip for insumo)
            if not db_producto.es_insumo and db_producto.ingredientes:
                ProductoService._recalcular_precio_producto(session, producto_id)

            uow.productos.add(db_producto)
            return db_producto

    @staticmethod
    def soft_delete(session: Session, producto_id: int):
        """Soft-delete a product by setting deleted_at.

        The row remains in the database for historical integrity.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None

            db_producto.deleted_at = get_utc_now()
            uow.productos.add(db_producto)
            return db_producto

    @staticmethod
    def get_ingredientes(session: Session, producto_id: int):
        """Get all ingredients associated with a product."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def get_categorias(session: Session, producto_id: int):
        """Get all categories associated with a product."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.productos.get_categorias(producto_id)

    @staticmethod
    def add_ingrediente(session: Session, producto_id: int, data: IngredienteAsignado):
        """Assign an ingredient to a product and recalculate the price."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None
            uow.productos.add_ingrediente_relacion(
                producto_id=producto_id,
                ingrediente_id=data.ingrediente_id,
                es_removible=data.es_removible,
                es_principal=data.es_principal,
                orden=data.orden,
                cantidad=data.cantidad,
            )
            # Recalculate price after ingredient change (skip for insumo)
            if not db_producto.es_insumo:
                ProductoService._recalcular_precio_producto(session, producto_id)
            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def remove_ingrediente(session: Session, producto_id: int, ingrediente_id: int):
        """Remove an ingredient association and recalculate price."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            result = uow.productos.delete_ingrediente_relacion(producto_id, ingrediente_id)
            if result:
                # Recalculate price after ingredient removal
                ProductoService._recalcular_precio_producto(session, producto_id)
            return result

    @staticmethod
    def update_ingrediente_cantidad(session: Session, producto_id: int, ingrediente_id: int, cantidad: int):
        """Update the cantidad of a ProductoIngrediente association.

        Returns the updated ingredient list on success, None if not found.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            repo = ProductoRepository(session)
            pi = repo.get_producto_ingrediente(producto_id, ingrediente_id)
            if not pi:
                return None

            pi.cantidad = cantidad
            uow.add(pi)

            # Recalculate price after quantity change
            ProductoService._recalcular_precio_producto(session, producto_id)

            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def add_categoria(session: Session, producto_id: int, data: "CategoriaAsignada"):
        """Assign a category to a product."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None
            uow.productos.add_categoria_relacion(
                producto_id=producto_id,
                categoria_id=data.categoria_id,
                es_principal=data.es_principal,
            )
            return uow.productos.get_categorias(producto_id)

    @staticmethod
    def remove_categoria(session: Session, producto_id: int, categoria_id: int):
        """Remove a category association."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            result = uow.productos.delete_categoria_relacion(producto_id, categoria_id)
            return result
