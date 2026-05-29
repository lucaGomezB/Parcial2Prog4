from fastapi import HTTPException
from sqlmodel import Session, col, select
from .models import Producto, ProductoMedida
from .schemas import ProductoCreate, ProductoUpdate, ProductoMedidaCreate, IngredienteAsignado, CategoriaAsignada
from models.base import get_utc_now
from ..Categoria.models import Categoria
from ..uow import CatalogoDeProductosUnitOfWork

class ProductoService:
    @staticmethod
    def _categoria_tiene_ancestro_primordial(session: Session, categoria_id: int) -> bool:
        """Walk up the category tree to check if this category or any ancestor is primordial."""
        visited = set()
        current_id = categoria_id
        while current_id is not None and current_id not in visited:
            visited.add(current_id)
            stmt = select(Categoria).where(
                Categoria.id == current_id,
                col(Categoria.deleted_at).is_(None),
            )
            cat = session.exec(stmt).first()
            if not cat:
                return False
            if cat.es_primordial:
                return True
            current_id = cat.parent_id
        return False

    @staticmethod
    def create(session: Session, data: ProductoCreate):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            # Validar ingredientes: si ninguna categoría seleccionada es primordial
            # (o descendiente de una), al menos 1 ingrediente es requerido
            tiene_cat_primordial = any(
                ProductoService._categoria_tiene_ancestro_primordial(session, cid)
                for cid in (data.categorias_ids or [])
            ) if data.categorias_ids else False
            if not tiene_cat_primordial and not data.ingredientes:
                raise HTTPException(
                    status_code=422,
                    detail="Se requiere al menos 1 ingrediente para crear un producto"
                )

            producto_data = data.model_dump(exclude={"categorias_ids", "categoria_principal_id", "ingredientes", "medidas"})
            db_producto = Producto(**producto_data)
            # Regla de negocio: stock 0 → no disponible automáticamente
            if db_producto.stock_cantidad == 0 and not data.medidas:
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
                    )

            if data.medidas:
                for m in data.medidas:
                    medida = ProductoMedida(
                        producto_id=db_producto.id,
                        nombre=m.nombre,
                        precio=m.precio,
                        stock=m.stock,
                        orden=m.orden,
                        disponible=m.disponible,
                    )
                    session.add(medida)
                # Si tiene medidas, disponible depende de disponibilidad + stock
                db_producto.disponible = any(m.disponible and m.stock > 0 for m in data.medidas)

            uow.commit()
            uow.productos.refresh(db_producto)
            return db_producto

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.productos.get_all(skip=skip, limit=limit)

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

            # Detectar si el producto tiene medidas (el stock se maneja por medida)
            tiene_medidas = bool(db_producto.medidas)

            values = data.model_dump(exclude_unset=True)

            # Guardar estado anterior para detectar transiciones
            old_disponible = db_producto.disponible

            for key, value in values.items():
                setattr(db_producto, key, value)

            # ── Reglas de stock que NO aplican si el producto usa medidas ──
            if not tiene_medidas:
                # Regla: si disponible cambió de False → True, sumar 1 al stock
                if db_producto.disponible is True and old_disponible is False:
                    db_producto.stock_cantidad = (db_producto.stock_cantidad or 0) + 1

                # Regla de negocio: stock 0 → no disponible automáticamente
                if db_producto.stock_cantidad == 0:
                    db_producto.disponible = False

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
            )
            uow.commit()
            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def remove_ingrediente(session: Session, producto_id: int, ingrediente_id: int):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            result = uow.productos.delete_ingrediente_relacion(producto_id, ingrediente_id)
            if result:
                uow.commit()
            return result

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

    # ── Medidas CRUD ──

    @staticmethod
    def listar_medidas(session: Session, producto_id: int):
        stmt = select(ProductoMedida).where(
            ProductoMedida.producto_id == producto_id
        ).order_by(ProductoMedida.orden)
        return session.exec(stmt).all()

    @staticmethod
    def crear_medida(session: Session, producto_id: int, data: ProductoMedidaCreate):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None
            medida = ProductoMedida(
                producto_id=producto_id,
                nombre=data.nombre,
                precio=data.precio,
                stock=data.stock,
                orden=data.orden,
                disponible=data.disponible,
            )
            session.add(medida)
            session.flush()
            # Actualizar disponible del producto según disponibilidad de medidas
            todas = ProductoService.listar_medidas(session, producto_id)
            db_producto.disponible = any(m.disponible and m.stock > 0 for m in todas)
            uow.commit()
            return medida

    @staticmethod
    def actualizar_medida(session: Session, producto_id: int, medida_id: int, data: ProductoMedidaCreate):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            stmt = select(ProductoMedida).where(
                ProductoMedida.id == medida_id,
                ProductoMedida.producto_id == producto_id,
            )
            medida = session.exec(stmt).first()
            if not medida:
                return None
            medida.nombre = data.nombre
            medida.precio = data.precio
            medida.stock = data.stock
            medida.orden = data.orden
            medida.disponible = data.disponible
            session.add(medida)
            # Actualizar disponible del producto según disponibilidad de medidas
            todas = ProductoService.listar_medidas(session, producto_id)
            db_producto = uow.productos.get_by_id(producto_id)
            if db_producto:
                db_producto.disponible = any(m.disponible and m.stock > 0 for m in todas)
            uow.commit()
            return medida

    @staticmethod
    def eliminar_medida(session: Session, producto_id: int, medida_id: int):
        with CatalogoDeProductosUnitOfWork(session) as uow:
            stmt = select(ProductoMedida).where(
                ProductoMedida.id == medida_id,
                ProductoMedida.producto_id == producto_id,
            )
            medida = session.exec(stmt).first()
            if not medida:
                return False
            session.delete(medida)
            # Actualizar disponible del producto
            todas = ProductoService.listar_medidas(session, producto_id)
            db_producto = uow.productos.get_by_id(producto_id)
            if db_producto:
                db_producto.disponible = any(m.stock > 0 for m in todas) if todas else (db_producto.stock_cantidad > 0)
            uow.commit()
            return True