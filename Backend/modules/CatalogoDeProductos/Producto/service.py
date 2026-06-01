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
from sqlmodel import Session, col, select
from .models import Producto
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
            uow.productos.add(db_producto)
            uow.productos.flush()

            if data.categorias_ids:
                for cat_id in data.categorias_ids:
                    uow.productos.add_categoria_relacion(
                        producto_id=db_producto.id,
                        categoria_id=cat_id,
                        es_principal=(cat_id == data.categoria_principal_id),
                    )

            if data.ingredientes:
                for ingrediente in data.ingredientes:
                    uow.productos.add_ingrediente_relacion(
                        producto_id=db_producto.id,
                        ingrediente_id=ingrediente.ingrediente_id,
                        es_removible=ingrediente.es_removible,
                        es_principal=ingrediente.es_principal,
                        orden=ingrediente.orden,
                        cantidad=ingrediente.cantidad,
                    )

            # Recalculate price if the product has ingredients
            if data.ingredientes:
                ProductoService._recalcular_precio_producto(session, db_producto.id)

            uow.commit()
            uow.productos.refresh(db_producto)
            return db_producto

    @staticmethod
    def _recalcular_precio_producto(session: Session, producto_id: int):
        """Recalculate precio_base = SUM(ingrediente.precio_actual * pi.cantidad).

        This method does NOT manage its own UoW — the calling method
        is responsible for the transaction boundary.
        """
        db_producto = session.get(Producto, producto_id)
        if not db_producto:
            return

        # Fetch all ProductoIngrediente associations for this product
        stmt = select(ProductoIngrediente).where(
            ProductoIngrediente.producto_id == producto_id,
        )
        associations = session.exec(stmt).all()

        if not associations:
            return

        total = Decimal('0')
        for pi in associations:
            ing = session.get(Ingrediente, pi.ingrediente_id)
            if ing and ing.precio_actual:
                total += ing.precio_actual * Decimal(pi.cantidad)

        db_producto.precio_base = total
        session.add(db_producto)

    @staticmethod
    def recalcular_precio_productos_afectados(session: Session, ingrediente_id: int):
        """Recalculate precio_base for ALL products using a given ingredient.

        Called automatically when an ingredient's price changes.
        Manages its own UoW transaction.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            stmt = select(ProductoIngrediente.producto_id).where(
                ProductoIngrediente.ingrediente_id == ingrediente_id,
            ).distinct()
            producto_ids = session.exec(stmt).all()

            for pid in producto_ids:
                ProductoService._recalcular_precio_producto(session, pid)

            uow.commit()

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100):
        """List all non-deleted products with pagination and ingredient flag.

        Read-only: does NOT use UoW because commit() would expire ORM objects,
        causing FastAPI serialization errors.

        The tiene_ingredientes flag is computed in a batch query to
        avoid N+1 checks per product.
        """
        from sqlmodel import select, col

        stmt = (
            select(Producto)
            .where(col(Producto.deleted_at).is_(None))
            .offset(skip).limit(limit)
            .order_by(Producto.id.desc())
        )
        productos = session.exec(stmt).all()

        if not productos:
            return productos

        # Batch-check which products have ingredient associations
        product_ids = [p.id for p in productos]
        stmt = select(ProductoIngrediente.producto_id).where(
            ProductoIngrediente.producto_id.in_(product_ids)
        ).distinct()
        rows = session.exec(stmt).all()
        ids_with_ingredients = set(rows)

        # Build ProductoRead response with computed tiene_ingredientes
        # Normalize NULL JSON fields before Pydantic validation
        result = []
        for p in productos:
            if p.imagenes_url is None:
                p.imagenes_url = []
            # model_validate does NOT include tiene_ingredientes (not a DB field),
            # so we exclude it from the dump and pass it explicitly.
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
        """Fetch a single non-deleted product by ID."""
        from sqlmodel import select, col

        stmt = (
            select(Producto)
            .where(Producto.id == producto_id)
            .where(col(Producto.deleted_at).is_(None))
        )
        return session.exec(stmt).first()

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
                stmt = select(ProductoIngrediente).where(
                    ProductoIngrediente.producto_id == producto_id,
                )
                associations = session.exec(stmt).all()

                for pi in associations:
                    ing = session.get(Ingrediente, pi.ingrediente_id)
                    if ing:
                        needed = pi.cantidad * diff
                        if ing.stock_actual < needed:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Stock insuficiente de '{ing.nombre}': necesita {needed} unidades, tiene {ing.stock_actual}"
                            )
                        ing.stock_actual -= needed
                        session.add(ing)

            # Rule: transitioning from unavailable to available adds 1 to stock
            if db_producto.disponible is True and old_disponible is False:
                db_producto.stock_cantidad = (db_producto.stock_cantidad or 0) + 1

            # Rule: zero stock forces unavailable
            if db_producto.stock_cantidad == 0:
                db_producto.disponible = False

            # Recalculate price if the product has ingredients
            if db_producto.ingredientes:
                ProductoService._recalcular_precio_producto(session, producto_id)

            uow.productos.add(db_producto)
            uow.commit()
            uow.productos.refresh(db_producto)
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
            uow.commit()
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
            # Recalculate price after ingredient change
            ProductoService._recalcular_precio_producto(session, producto_id)
            uow.commit()
            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def remove_ingrediente(session: Session, producto_id: int, ingrediente_id: int):
        """Remove an ingredient association and recalculate the price."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            result = uow.productos.delete_ingrediente_relacion(producto_id, ingrediente_id)
            if result:
                # Recalculate price after ingredient removal
                ProductoService._recalcular_precio_producto(session, producto_id)
                uow.commit()
            return result

    @staticmethod
    def update_ingrediente_cantidad(session: Session, producto_id: int, ingrediente_id: int, cantidad: int):
        """Update the cantidad of a ProductoIngrediente association.

        Returns the updated ingredient list on success, None if not found.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            stmt = select(ProductoIngrediente).where(
                ProductoIngrediente.producto_id == producto_id,
                ProductoIngrediente.ingrediente_id == ingrediente_id,
            )
            pi = session.exec(stmt).first()
            if not pi:
                return None

            pi.cantidad = cantidad
            session.add(pi)

            # Recalculate price after quantity change
            ProductoService._recalcular_precio_producto(session, producto_id)

            uow.commit()
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
            uow.commit()
            return uow.productos.get_categorias(producto_id)

    @staticmethod
    def remove_categoria(session: Session, producto_id: int, categoria_id: int):
        """Remove a category association."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            result = uow.productos.delete_categoria_relacion(producto_id, categoria_id)
            if result:
                uow.commit()
            return result
