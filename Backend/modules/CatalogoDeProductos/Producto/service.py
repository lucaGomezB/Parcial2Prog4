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
    @staticmethod
    def create(session: Session, data: ProductoCreate):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            # Siempre requerir ingredientes
            if not data.ingredientes:
                raise HTTPException(
                    status_code=422,
                    detail="Se requiere al menos 1 ingrediente para crear un producto"
                )

            producto_data = data.model_dump(exclude={"categorias_ids", "categoria_principal_id", "ingredientes"})
            db_producto = Producto(**producto_data)
            # Regla de negocio: stock 0 → no disponible automáticamente
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

            # Recalcular precio_base si el producto tiene ingredientes
            if data.ingredientes:
                ProductoService._recalcular_precio_producto(session, db_producto.id)

            uow.commit()
            uow.productos.refresh(db_producto)
            return db_producto

    @staticmethod
    def _recalcular_precio_producto(session: Session, producto_id: int):
        """Recalcula precio_base = SUM(ingrediente.precio_actual * pi.cantidad).
        NO maneja UoW — la transacción debe ser manejada por quien llama."""
        db_producto = session.get(Producto, producto_id)
        if not db_producto:
            return

        # Obtener todas las asociaciones ProductoIngrediente del producto
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
                total += ing.precio_actual * pi.cantidad

        db_producto.precio_base = total
        session.add(db_producto)

    @staticmethod
    def recalcular_precio_productos_afectados(session: Session, ingrediente_id: int):
        """Recalcula precio_base de todos los productos que usan un ingrediente.
        Maneja su propia transacción UoW."""
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
        with CatalogoDeProductosUnitOfWork(session) as uow:
            productos = uow.productos.get_all(skip=skip, limit=limit)

            if not productos:
                return productos

            # Batch check which products have ingredient associations
            product_ids = [p.id for p in productos]
            stmt = select(ProductoIngrediente.producto_id).where(
                ProductoIngrediente.producto_id.in_(product_ids)
            ).distinct()
            rows = session.exec(stmt).all()
            ids_with_ingredients = set(rows)

            # Build ProductoRead with tiene_ingredientes populated
            return [
                ProductoRead(
                    **ProductoRead.model_validate(p).model_dump(),
                    tiene_ingredientes=p.id in ids_with_ingredients,
                )
                for p in productos
            ]

    @staticmethod
    def get_by_id(session: Session, producto_id: int):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.productos.get_by_id(producto_id)

    @staticmethod
    def update(session: Session, producto_id: int, data: ProductoUpdate):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None

            values = data.model_dump(exclude_unset=True)

            # Guardar estado anterior para detectar transiciones
            old_disponible = db_producto.disponible

            for key, value in values.items():
                setattr(db_producto, key, value)

            # Regla: si disponible cambió de False → True, sumar 1 al stock
            if db_producto.disponible is True and old_disponible is False:
                db_producto.stock_cantidad = (db_producto.stock_cantidad or 0) + 1

            # Regla de negocio: stock 0 → no disponible automáticamente
            if db_producto.stock_cantidad == 0:
                db_producto.disponible = False

            # Recalcular precio_base si el producto tiene ingredientes
            if db_producto.ingredientes:
                ProductoService._recalcular_precio_producto(session, producto_id)

            uow.productos.add(db_producto)
            uow.commit()
            uow.productos.refresh(db_producto)
            return db_producto

    @staticmethod
    def soft_delete(session: Session, producto_id: int):
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
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def get_categorias(session: Session, producto_id: int):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.productos.get_categorias(producto_id)

    @staticmethod
    def add_ingrediente(session: Session, producto_id: int, data: IngredienteAsignado):
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
            # Recalcular precio_base del producto
            ProductoService._recalcular_precio_producto(session, producto_id)
            uow.commit()
            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def remove_ingrediente(session: Session, producto_id: int, ingrediente_id: int):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            result = uow.productos.delete_ingrediente_relacion(producto_id, ingrediente_id)
            if result:
                # Recalcular precio_base del producto
                ProductoService._recalcular_precio_producto(session, producto_id)
                uow.commit()
            return result

    @staticmethod
    def update_ingrediente_cantidad(session: Session, producto_id: int, ingrediente_id: int, cantidad: Decimal):
        """Update the cantidad of a ProductoIngrediente association.
        Returns the updated ingredient list on success, None if not found."""
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

            # Recalcular precio_base del producto
            ProductoService._recalcular_precio_producto(session, producto_id)

            uow.commit()
            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def add_categoria(session: Session, producto_id: int, data: "CategoriaAsignada"):
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
        with CatalogoDeProductosUnitOfWork(session) as uow:
            result = uow.productos.delete_categoria_relacion(producto_id, categoria_id)
            if result:
                uow.commit()
            return result

