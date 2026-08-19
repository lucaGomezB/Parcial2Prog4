"""
Producto service — business logic for product CRUD, ingredient/category
management, and automatic price recalculation.

This is the thickest layer in the Product module. Key invariants:
- precio_base is auto-calculated from ingredient costs when ingredients exist
- Stock transitions can trigger ingredient stock consumption
- Soft-delete is used (no physical row removal)
- All write operations use the Unit of Work pattern
"""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlmodel import Session, select
from typing import Optional
from collections import defaultdict
from .models import Producto
from .schemas import ProductoCreate, ProductoRead, ProductoUpdate, IngredienteAsignado, CategoriaAsignada
from app.core.paginated_response import PaginatedResponse
from app.core.base import get_utc_now
from ..Categoria.models import Categoria
from ..HistorialStock.service import HistorialStockService
from ..Ingrediente.models import Ingrediente
from ..producto_ingrediente import ProductoIngrediente
from ..uow import CatalogoDeProductosUnitOfWork
from ..utils import convertir_cantidad as _convertir_cantidad, load_conversion_factors as _load_conversion_factors
from app.core.dependencies import get_ws_manager, fire_broadcast


class ProductoService:

    @staticmethod
    def create(session: Session, data: ProductoCreate, ws_manager=None):
        """Create a product with optional ingredient association.

        Business rules:
        - stock_cantidad and disponible are independent flags
        - The price is recalculated from ingredients if any are assigned
        """
        # Block ingredient assignment to finished products
        if data.es_producto_terminado and data.ingredientes:
            raise HTTPException(
                status_code=400,
                detail="No se pueden asignar ingredientes a un producto terminado"
            )

        # Default to Porcion (ID 5) if no unit provided
        if getattr(data, 'unidad_medida_id', None) is None:
            data.unidad_medida_id = 5

        with CatalogoDeProductosUnitOfWork(session) as uow:
            producto_data = data.model_dump(exclude={"categorias_ids", "categoria_principal_id", "ingredientes"})
            db_producto = Producto(**producto_data)

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
            # and is not marked as a producto terminado (resold item with manual price).
            if not data.es_producto_terminado and (not data.ingredientes) and db_producto.precio_base <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="El precio base debe ser mayor a 0 cuando el producto no tiene ingredientes ni es de reventa"
                )

            uow.productos.create(db_producto)

            if data.categorias_ids:
                for cat_id in data.categorias_ids:
                    uow.productos.add_categoria_relacion(
                        producto_id=db_producto.id,
                        categoria_id=cat_id,
                        es_principal=(cat_id == data.categoria_principal_id),
                    )

            # Skip ingredient block entirely for producto terminado products
            if not data.es_producto_terminado and data.ingredientes:
                for ingrediente in data.ingredientes:
                    uow.productos.add_ingrediente_relacion(
                        producto_id=db_producto.id,
                        ingrediente_id=ingrediente.ingrediente_id,
                        es_removible=ingrediente.es_removible,
                        es_principal=ingrediente.es_principal,
                        orden=ingrediente.orden,
                        cantidad=ingrediente.cantidad,
                        unidad_medida_id=ingrediente.unidad_medida_id,
                    )

            # Sync price and derived stock from ingredients (also syncs stock_manual for terminado)
            if data.ingredientes or data.es_producto_terminado:
                ProductoService._recalcular_precio_producto(uow, db_producto.id)

            # ── Ingredient stock: log creation if stock > 0 ──
            if db_producto.stock_cantidad > 0:
                HistorialStockService.registrar_cambio(
                    uow,
                    entidad_tipo="producto",
                    entidad_id=db_producto.id,
                    stock_anterior=0,
                    stock_nuevo=db_producto.stock_cantidad,
                    motivo="creacion",
                    usuario_id=data.usuario_id if hasattr(data, 'usuario_id') else None,
                )

            # NOTE: do NOT call session.refresh() here. refresh() discards
            # uncommitted attribute changes; it would revert the derived
            # stock_cantidad (and any other field) set by
            # _recalcular_precio_producto back to the DB value (0).
            result_producto = db_producto

        # ── AFTER commit: broadcast stock_actualizado ──
        if ws_manager is None:
            try:
                ws_manager = get_ws_manager()
            except Exception:
                pass
        if ws_manager is not None and result_producto.stock_cantidad > 0:
            payload = {
                "event": "stock_actualizado",
                "entidad_tipo": "producto",
                "entidad_id": result_producto.id,
                "entidad_nombre": result_producto.nombre,
                "stock_anterior": 0,
                "stock_nuevo": result_producto.stock_cantidad,
                "motivo": "creacion",
                "usuario_id": data.usuario_id if hasattr(data, 'usuario_id') else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            fire_broadcast(ws_manager, f"producto_{result_producto.id}", payload)
            fire_broadcast(ws_manager, "stock_admin", payload)

        return result_producto

    # ── Shared ingredient helpers ─────────────────────────────────────────
    # NOTE: _restore_ingredient_stock and _deduct_ingredient_stock have been
    # REMOVED. Under the make-to-order model, ingredient stock is consumed
    # at order confirmation time (PedidoService), not at manufacturing time
    # (ProductoService). Product stock is now derived from ingredient
    # availability, not stored in a writable column.

    @staticmethod
    def _recalcular_precio_producto(uow: CatalogoDeProductosUnitOfWork, producto_id: int):
        """Recalculate precio_base and derived stock from ingredient data.

        precio_base = SUM(ingrediente.precio_actual * pi.cantidad convertida)
        stock_cantidad = compute_derived_stock (or stock_manual for terminado)

        This method does NOT manage its own UoW — the calling method
        is responsible for the transaction boundary. All writes go through uow.add().
        """
        factores = _load_conversion_factors(uow.session)
        db_producto = uow.productos.get_with_ingredients(producto_id)
        if not db_producto:
            return

        # ── producto terminado: precio is manual, stock = stock_manual ──
        if db_producto.es_producto_terminado:
            db_producto.stock_cantidad = db_producto.stock_manual or 0
            uow.productos.update(db_producto)
            return

        # Fetch all ProductoIngrediente associations for this product
        associations = uow.productos.get_producto_ingredientes(producto_id)

        if not associations:
            db_producto.stock_cantidad = 0
            uow.productos.update(db_producto)
            return

        total = Decimal('0')
        for pi in associations:
            ing = uow.productos.get_ingrediente(pi.ingrediente_id)
            if ing and ing.precio_actual:
                # Convert: pi.cantidad (in pi.unidad_medida) → ing.unidad_medida
                # Fallback: if pi.unidad_medida_id is None, default to the
                # ingredient's own unit so the quantity is not misinterpreted.
                pi_unidad = pi.unidad_medida_id or ing.unidad_medida_id
                cantidad_convertida = _convertir_cantidad(
                    Decimal(pi.cantidad),
                    pi_unidad,
                    ing.unidad_medida_id,
                    factores=factores,
                )
                total += ing.precio_actual * cantidad_convertida

        old_precio_base = db_producto.precio_base
        db_producto.precio_base = total

        # ── Proportional price adjustment ──
        # When ingredient costs change, scale precio_actual proportionally
        # to preserve the markup margin. PrecioVenta_nuevo = PrecioVenta_viejo * (PrecioBase_nuevo / PrecioBase_viejo)
        if old_precio_base > 0 and db_producto.precio_actual > 0:
            ratio = db_producto.precio_base / old_precio_base
            db_producto.precio_actual = db_producto.precio_actual * ratio

        # Safety net: precio_actual must never fall below precio_base
        if db_producto.precio_actual < db_producto.precio_base:
            db_producto.precio_actual = db_producto.precio_base

        # Sync derived stock from ingredient availability
        stock_derivado = uow.productos.compute_derived_stock(producto_id)
        db_producto.stock_cantidad = stock_derivado

        uow.productos.update(db_producto)

    @staticmethod
    def recalcular_precio_productos_afectados(session: Session, ingrediente_id: int):
        """Recalculate precio_base for ALL products using a given ingredient.

        Called automatically when an ingredient's price changes.
        Manages its own UoW transaction. The UoW __exit__ handles commit.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            producto_ids = uow.productos.get_productos_afectados(ingrediente_id)

            # Exclude producto terminado products from recalculation (their price is manual).
            # Single batch query instead of N+1 individual session.get() calls.
            if producto_ids:
                producto_terminado_ids = uow.productos.get_producto_terminado_ids(producto_ids)
                producto_ids = [pid for pid in producto_ids if pid not in producto_terminado_ids]

            for pid in producto_ids:
                ProductoService._recalcular_precio_producto(uow, pid)

            # NOTE: No manual uow.commit() — the UoW __exit__ handles it automatically.

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None, categoria_id: Optional[list[int]] = None, sort_by: Optional[str] = None, sort_order: Optional[str] = None) -> PaginatedResponse[ProductoRead]:
        """List all non-deleted products with pagination, ingredient flag, optional text search, and optional category filter.

        When categoria_id is provided (single ID or list), the filter includes each category
        and all its descendants (union via get_descendant_ids on the category repository).

        Read-only: wrapped in UoW for consistent DB access. The data is already
        in memory when returned so the UoW commit on exit is harmless.

        The tiene_ingredientes flag is computed in a batch query to
        avoid N+1 checks per product.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            # Resolve descendant category IDs when filtering by category
            # Supports both single int (backward compat) and list[int] (multi-select)
            categoria_ids: Optional[list[int]] = None
            if categoria_id:
                all_ids: set[int] = set()
                for cid in categoria_id:
                    all_ids.update(uow.categorias.get_descendant_ids(cid))
                categoria_ids = list(all_ids)

            productos, ids_with_ingredients = uow.productos.get_all_with_ingredient_flag(
                skip=skip, limit=limit, search=search, categoria_ids=categoria_ids,
                sort_by=sort_by, sort_order=sort_order,
            )
            total = uow.productos.count_all(search=search, categoria_ids=categoria_ids)

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

            # Populate categoria_ids on each ProductoRead via batch query
            if result:
                product_ids = [p.id for p in result]
                from ..producto_categoria import ProductoCategoria as PC
                pc_stmt = select(PC).where(PC.producto_id.in_(product_ids))
                pc_rows = session.exec(pc_stmt).all()
                pc_map = defaultdict(list)
                for row in pc_rows:
                    pc_map[row.producto_id].append(row.categoria_id)
                # Build new list with populated categoria_ids
                enriched = []
                for p in result:
                    p_dict = p.model_dump()
                    p_dict['categoria_ids'] = pc_map.get(p.id, [])
                    enriched.append(ProductoRead(**p_dict))
                result = enriched

            return PaginatedResponse(
                items=result,
                total=total,
                skip=skip,
                limit=limit,
            )

    @staticmethod
    def get_by_id(session: Session, producto_id: int):
        """Fetch a single non-deleted product by ID.

        Read-only: wrapped in UoW for consistent DB access.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.productos.get_with_ingredients(producto_id)

    @staticmethod
    def update(session: Session, producto_id: int, data: ProductoUpdate, ws_manager=None):
        """Update a product (make-to-order model).

        Key business rules:
        - Product stock is derived from ingredient availability (not directly managed)
        - Ingredient associations can be replaced without stock reconciliation
        - es_producto_terminado toggle deletes PI associations (no restore needed)
        - Price is recalculated if the product has ingredients
        """
        stock_changed = False  # Track whether stock was modified
        with CatalogoDeProductosUnitOfWork(session) as uow:
            # SELECT FOR UPDATE: lock the row to prevent race conditions
            # with concurrent order confirmations modifying the same product.
            db_producto = uow.productos.get_by_id(producto_id, for_update=True)
            if not db_producto:
                return None

            # Task 5.5: Handle ingredientes field — pop from the raw model
            # BEFORE model_dump so we keep IngredienteAsignado objects (not dicts).
            nuevos_ingredientes = data.ingredientes

            values = data.model_dump(exclude_unset=True, exclude={"ingredientes"})

            # Track state before applying changes, for transition detection
            old_stock = db_producto.stock_cantidad
            old_es_producto_terminado = db_producto.es_producto_terminado

            for key, value in values.items():
                setattr(db_producto, key, value)

            new_stock = db_producto.stock_cantidad

            # M4 (make-to-order): es_producto_terminado toggle — delete PI associations.
            # No stock reconciliation needed (ingredients are consumed at order time).
            if 'es_producto_terminado' in values and old_es_producto_terminado is False and db_producto.es_producto_terminado is True:
                existing_pi = uow.productos.get_producto_ingredientes(producto_id)
                for pi in existing_pi:
                    uow.delete(pi)
                # Clear the ingredientes relationship so downstream checks work correctly
                db_producto.ingredientes = []

            # NOTE: Under make-to-order, stock_cantidad is derived from ingredients.
            # Manual stock_cantidad changes no longer reconcile ingredient stock.
            # The field remains writable for manual adjustments but no longer
            # triggers ingredient consumption or restoration.

            # Block ingredient assignment to finished products on update
            if db_producto.es_producto_terminado and nuevos_ingredientes:
                raise HTTPException(
                    status_code=400,
                    detail="No se pueden asignar ingredientes a un producto terminado"
                )

            # Task 5.5 + M3: Handle ingredientes field — full replacement of ingredient list.
            # Under make-to-order, no stock reconciliation needed (consumed at order time).
            if nuevos_ingredientes is not None:
                # Delete all existing ingredient associations for this product
                existing = uow.productos.get_producto_ingredientes(producto_id)
                for pi in existing:
                    uow.delete(pi)

                # Create new associations from the provided list
                for ing_data in nuevos_ingredientes:
                    uow.productos.add_ingrediente_relacion(
                        producto_id=producto_id,
                        ingrediente_id=ing_data.ingrediente_id,
                        es_removible=ing_data.es_removible,
                        es_principal=ing_data.es_principal,
                        orden=ing_data.orden,
                        cantidad=ing_data.cantidad,
                        unidad_medida_id=ing_data.unidad_medida_id,
                    )

            # Validate: if precio_actual was updated, it must not be lower than precio_base
            if 'precio_actual' in values and db_producto.precio_actual < db_producto.precio_base:
                raise HTTPException(
                    status_code=400,
                    detail="El precio actual no puede ser menor al precio base"
                )

            # Validate price after updates: must be > 0 when the product
            # has no ingredients and is not a producto terminado (resold item).
            if not db_producto.es_producto_terminado and not db_producto.ingredientes and db_producto.precio_base <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="El precio base debe ser mayor a 0 cuando el producto no tiene ingredientes ni es de reventa"
                )

            # For terminado products, sync stock_cantidad -> stock_manual
            # before recalc. stock_cantidad is the user-facing field; stock_manual
            # is the persistent source of truth for terminado products.
            if db_producto.es_producto_terminado and 'stock_cantidad' in values:
                db_producto.stock_manual = int(values['stock_cantidad'])

            # Sync price and derived stock (also syncs stock_manual for terminado)
            # NOTE: Check nuevos_ingredientes OR db_producto.ingredientes because
            # after a full ingredient replacement (delete-all + re-add), the ORM
            # relationship may be stale until the session is flushed/refreshed.
            if nuevos_ingredientes is not None or db_producto.ingredientes or db_producto.es_producto_terminado:
                ProductoService._recalcular_precio_producto(uow, producto_id)

            # ── Stock audit: log if stock changed ──
            stock_changed = 'stock_cantidad' in values and new_stock != old_stock
            if stock_changed:
                HistorialStockService.registrar_cambio(
                    uow,
                    entidad_tipo="producto",
                    entidad_id=producto_id,
                    stock_anterior=old_stock,
                    stock_nuevo=new_stock,
                    motivo="actualizacion",
                    usuario_id=None,
                )

            uow.productos.update(db_producto)
            result_producto = db_producto

        # ── AFTER commit: broadcast stock_actualizado if stock changed ──
        if stock_changed:
            if ws_manager is None:
                try:
                    ws_manager = get_ws_manager()
                except Exception:
                    pass
            if ws_manager is not None:
                payload = {
                    "event": "stock_actualizado",
                    "entidad_tipo": "producto",
                    "entidad_id": result_producto.id,
                    "entidad_nombre": result_producto.nombre,
                    "stock_anterior": old_stock,
                    "stock_nuevo": new_stock,
                    "motivo": "actualizacion",
                    "usuario_id": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                fire_broadcast(ws_manager, f"producto_{result_producto.id}", payload)
                fire_broadcast(ws_manager, "stock_admin", payload)

        return result_producto

    @staticmethod
    def soft_delete(session: Session, producto_id: int, ws_manager=None):
        """Soft-delete a product by setting deleted_at.

        Under make-to-order, ingredient stock is consumed at order time,
        not at manufacturing time. No stock reconciliation is needed on delete.
        The row remains in the database for historical integrity.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None

            old_stock = db_producto.stock_cantidad

            # ── Stock audit: log soft_delete ──
            HistorialStockService.registrar_cambio(
                uow,
                entidad_tipo="producto",
                entidad_id=producto_id,
                stock_anterior=old_stock,
                stock_nuevo=old_stock,
                motivo="soft_delete",
                usuario_id=None,
            )

            db_producto.deleted_at = get_utc_now()
            uow.productos.update(db_producto)
            result_producto = db_producto

        # ── AFTER commit: broadcast stock_actualizado ──
        if ws_manager is None:
            try:
                ws_manager = get_ws_manager()
            except Exception:
                pass
        if ws_manager is not None:
            payload = {
                "event": "stock_actualizado",
                "entidad_tipo": "producto",
                "entidad_id": result_producto.id,
                "entidad_nombre": result_producto.nombre,
                "stock_anterior": old_stock,
                "stock_nuevo": old_stock,
                "motivo": "soft_delete",
                "usuario_id": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            fire_broadcast(ws_manager, f"producto_{result_producto.id}", payload)
            fire_broadcast(ws_manager, "stock_admin", payload)

        return result_producto

    @staticmethod
    def get_ingredientes(session: Session, producto_id: int):
        """Get all ingredients associated with a product."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def get_ingredientes_stock_detail(session: Session, producto_id: int):
        """Get per-ingredient stock breakdown showing limiting factors."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            producto = uow.productos.get_by_id(producto_id)
            if not producto:
                return None
            return uow.productos.get_ingredientes_stock_detail(producto_id)

    @staticmethod
    def get_categorias(session: Session, producto_id: int):
        """Get all categories associated with a product."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            return uow.productos.get_categorias(producto_id)

    @staticmethod
    def get_ingredientes_compartidos(session: Session):
        """Map each product to the ingredient names it shares with other products."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            mapping = uow.productos.get_ingredientes_compartidos()
        return [
            {"producto_id": producto_id, "ingredientes": nombres}
            for producto_id, nombres in mapping.items()
        ]

    @staticmethod
    def add_ingrediente(session: Session, producto_id: int, data: IngredienteAsignado):
        """Assign an ingredient to a product, reconcile stock, and recalculate the price.

        M5a (fix-stock-reconciliation): If the product has stock > 0, validate the
        ingredient has sufficient stock and deduct accordingly.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None
            if db_producto.es_producto_terminado:
                raise HTTPException(
                    status_code=400,
                    detail="No se pueden asignar ingredientes a un producto terminado"
                )
            uow.productos.add_ingrediente_relacion(
                producto_id=producto_id,
                ingrediente_id=data.ingrediente_id,
                es_removible=data.es_removible,
                es_principal=data.es_principal,
                orden=data.orden,
                cantidad=data.cantidad,
                unidad_medida_id=data.unidad_medida_id,
            )

            # Recalculate price after ingredient change (skip for insumo)
            if not db_producto.es_producto_terminado:
                ProductoService._recalcular_precio_producto(uow, producto_id)
            return uow.productos.get_ingredientes(producto_id)

    @staticmethod
    def remove_ingrediente(session: Session, producto_id: int, ingrediente_id: int):
        """Remove an ingredient association and recalculate price.

        Under make-to-order, ingredient stock is consumed at order time.
        No stock reconciliation is needed on ingredient removal.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None
            if db_producto.es_producto_terminado:
                raise HTTPException(
                    status_code=400,
                    detail="No se pueden gestionar ingredientes de un producto terminado"
                )
            result = uow.productos.delete_ingrediente_relacion(producto_id, ingrediente_id)
            if result:
                # Recalculate price after ingredient removal
                ProductoService._recalcular_precio_producto(uow, producto_id)
            return result

    @staticmethod
    def update_ingrediente(session: Session, producto_id: int, ingrediente_id: int, data: "IngredienteAsignado"):
        """Update a ProductoIngrediente association (cantidad, removible, principal, unidad).

        Under make-to-order, ingredient stock is consumed at order time.
        No stock reconciliation is needed on ingredient quantity changes.

        Returns the updated ingredient list on success, None if not found.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_producto = uow.productos.get_by_id(producto_id)
            if not db_producto:
                return None
            if db_producto.es_producto_terminado:
                raise HTTPException(
                    status_code=400,
                    detail="No se pueden gestionar ingredientes de un producto terminado"
                )
            pi = uow.productos.get_producto_ingrediente(producto_id, ingrediente_id)
            if not pi:
                return None

            pi.cantidad = data.cantidad
            pi.es_removible = data.es_removible
            pi.es_principal = data.es_principal
            if data.unidad_medida_id is not None:
                pi.unidad_medida_id = data.unidad_medida_id
            uow.add(pi)

            # Recalculate price after change
            ProductoService._recalcular_precio_producto(uow, producto_id)

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
