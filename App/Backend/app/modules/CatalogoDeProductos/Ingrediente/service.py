"""
Ingrediente service — business logic for ingredient CRUD.

Key behaviors:
- Price changes trigger automatic recalculation of all affected product prices
- Duplicate ingredient names are caught via IntegrityError
- Read operations avoid UoW to prevent ORM object expiration
- Stock and price have dedicated update endpoints with side effects
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Session, select
from typing import List, Optional
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)
from app.core.routing import get_or_404
from sqlalchemy.exc import IntegrityError
from .models import Ingrediente
from .schemas import IngredienteCreate, IngredienteRead, IngredienteUpdate
from app.core.paginated_response import PaginatedResponse
from app.core.base import get_utc_now
from ..HistorialStock.service import HistorialStockService
from ..uow import CatalogoDeProductosUnitOfWork
from ..Producto.service import ProductoService
from ..Producto.models import Producto
from ..producto_ingrediente import ProductoIngrediente
from ..UnidadMedida.models import UnidadMedida
from app.core.dependencies import get_ws_manager


class IngredienteService:
    """Business logic for Ingredient CRUD and automatic price propagation."""

    @staticmethod
    def create(session: Session, data: IngredienteCreate, ws_manager=None) -> Ingrediente:
        """Create a new ingredient with duplicate name handling."""
        # Validate unidad_medida_id exists (if provided)
        if data.unidad_medida_id is not None:
            unidad = session.exec(
                select(UnidadMedida).where(UnidadMedida.id == data.unidad_medida_id)
            ).first()
            if not unidad:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unidad de medida con id {data.unidad_medida_id} no encontrada.",
                )

        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = Ingrediente.model_validate(data)
            try:
                uow.ingredientes.create(db_ingrediente)
            except IntegrityError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe un ingrediente con ese nombre. No se puede crear duplicados.",
                )

            # ── Stock audit: log creation if stock > 0 ──
            if db_ingrediente.stock_actual > 0:
                HistorialStockService.registrar_cambio(
                    uow,
                    entidad_tipo="ingrediente",
                    entidad_id=db_ingrediente.id,
                    stock_anterior=0,
                    stock_nuevo=db_ingrediente.stock_actual,
                    motivo="creacion",
                )

            result = db_ingrediente

        # ── AFTER commit: broadcast to stock_admin ──
        if ws_manager is None:
            ws_manager = get_ws_manager()
        if ws_manager is not None and result.stock_actual > 0:
            from app.core.dependencies import fire_broadcast
            payload = {
                "event": "stock_actualizado",
                "entidad_tipo": "ingrediente",
                "entidad_id": result.id,
                "entidad_nombre": result.nombre,
                "stock_anterior": 0,
                "stock_nuevo": result.stock_actual,
                "motivo": "creacion",
                "usuario_id": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            fire_broadcast(ws_manager, "stock_admin", payload)

        return result

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100, search: Optional[str] = None) -> PaginatedResponse[IngredienteRead]:
        """List non-deleted ingredients with pagination and optional text search.

        Read-only: wrapped in UoW for consistent DB access.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            rows = uow.ingredientes.get_all_paginated(skip=skip, limit=limit, search=search)
            total = uow.ingredientes.count_all(search=search)
            return PaginatedResponse(
                items=[IngredienteRead.model_validate(r) for r in rows],
                total=total,
                skip=skip,
                limit=limit,
            )

    @staticmethod
    def get_by_id(session: Session, ingrediente_id: int) -> Optional[IngredienteRead]:
        """Fetch a single non-deleted ingredient by ID.

        Read-only: wrapped in UoW for consistent DB access.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            row = uow.ingredientes.get_by_id(ingrediente_id)
            if not row:
                return None
            return IngredienteRead.model_validate(row)

    @staticmethod
    def actualizar_precio(session: Session, ingrediente_id: int, precio: Decimal, ws_manager=None) -> Ingrediente:
        """Update ingredient price and trigger recalculation of all affected products.

        This is the key method that propagates ingredient price changes
        through the product catalog.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            get_or_404(db_ingrediente, "Ingrediente no encontrado")
            db_ingrediente.precio_actual = precio
            uow.ingredientes.update(db_ingrediente)
        # Refresh after commit to get current state
        session.refresh(db_ingrediente)
        # Trigger price recalculation for all products using this ingredient
        ProductoService.recalcular_precio_productos_afectados(session, ingrediente_id)

        # ── AFTER commit: broadcast price updates to affected products ──
        if ws_manager is None:
            ws_manager = get_ws_manager()
        if ws_manager is not None:
            try:
                from app.modules.CatalogoDeProductos.stock_ws_router import (
                    broadcast_price_update_for_products,
                )
                # Query affected product IDs using a fresh UoW context
                with CatalogoDeProductosUnitOfWork(session) as uow2:
                    producto_ids = uow2.productos.get_productos_afectados_por_ingrediente(ingrediente_id)
                if producto_ids:
                    broadcast_price_update_for_products(
                        session, producto_ids, ws_manager,
                        motivo="ingrediente_precio_actualizado",
                    )
            except Exception:
                logger.exception(
                    "Failed to broadcast price update after ingredient %s price change",
                    ingrediente_id,
                )

        return db_ingrediente

    @staticmethod
    def actualizar_stock(session: Session, ingrediente_id: int, stock: int, ws_manager=None) -> Ingrediente:
        """Update ingredient stock. Does NOT affect product prices.

        Gap 1 (fix-stock-reconciliation): Validates that stock is not negative
        before setting, returning 400 instead of a cryptic DB error.
        """
        if stock < 0:
            raise HTTPException(
                status_code=400,
                detail="El stock no puede ser negativo",
            )
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            get_or_404(db_ingrediente, "Ingrediente no encontrado")
            old_stock = db_ingrediente.stock_actual
            db_ingrediente.stock_actual = stock
            uow.ingredientes.update(db_ingrediente)

            # ── Stock audit ──
            HistorialStockService.registrar_cambio(
                uow,
                entidad_tipo="ingrediente",
                entidad_id=ingrediente_id,
                stock_anterior=old_stock,
                stock_nuevo=stock,
                motivo="actualizacion",
            )

            # ── Phase 3: Propagate derived stock changes to affected products (INSIDE UoW) ──
            if ws_manager is None:
                ws_manager = get_ws_manager()
            if ws_manager is not None:
                from app.modules.CatalogoDeProductos.stock_ws_router import (
                    broadcast_derived_stock_for_products,
                )
                producto_ids = uow.productos.get_productos_afectados_por_ingrediente(ingrediente_id)
                if producto_ids:
                    broadcast_derived_stock_for_products(
                        session, producto_ids, ws_manager, motivo="ingrediente_actualizado",
                    )

            result = db_ingrediente

        # Refresh after commit to get current state
        session.refresh(result)

        # ── AFTER commit: broadcast to stock_admin ──
        if ws_manager is None:
            ws_manager = get_ws_manager()
        if ws_manager is not None:
            from app.core.dependencies import fire_broadcast
            payload = {
                "event": "stock_actualizado",
                "entidad_tipo": "ingrediente",
                "entidad_id": result.id,
                "entidad_nombre": result.nombre,
                "stock_anterior": old_stock,
                "stock_nuevo": stock,
                "motivo": "actualizacion",
                "usuario_id": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            fire_broadcast(ws_manager, "stock_admin", payload)

        return result

    @staticmethod
    def update(session: Session, ingrediente_id: int, data: IngredienteUpdate, ws_manager=None) -> Optional[Ingrediente]:
        """Update an ingredient. Triggers price recalculation if precio_actual changed."""
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            if not db_ingrediente:
                return None

            old_stock = db_ingrediente.stock_actual

            values = data.model_dump(exclude_unset=True)

            # Track if unit changed — used for post-commit recalculation
            unidad_cambio = False
            if (
                "unidad_medida_id" in values
                and values["unidad_medida_id"] != db_ingrediente.unidad_medida_id
            ):
                unidad_cambio = True

            for key, value in values.items():
                setattr(db_ingrediente, key, value)

            new_stock = db_ingrediente.stock_actual

            # ── Stock audit: log if stock changed ──
            if old_stock != new_stock:
                HistorialStockService.registrar_cambio(
                    uow,
                    entidad_tipo="ingrediente",
                    entidad_id=ingrediente_id,
                    stock_anterior=old_stock,
                    stock_nuevo=new_stock,
                    motivo="actualizacion",
                )

            # ── Recalculate affected products if unit changed (INSIDE UoW) ──
            if unidad_cambio:
                ProductoService.recalcular_precio_productos_afectados(session, ingrediente_id)
                try:
                    from app.modules.CatalogoDeProductos.stock_ws_router import broadcast_derived_stock_for_products
                    from app.modules.CatalogoDeProductos.stock_ws_router import broadcast_price_update_for_products
                    producto_ids = uow.productos.get_productos_afectados_por_ingrediente(ingrediente_id)
                    if producto_ids:
                        if ws_manager is None:
                            ws_manager = get_ws_manager()
                        broadcast_derived_stock_for_products(
                            session, producto_ids, ws_manager, motivo="ingrediente_unidad_cambiada",
                        )
                        broadcast_price_update_for_products(
                            session, producto_ids, ws_manager, motivo="ingrediente_unidad_cambiada",
                        )
                except Exception:
                    logger.exception(
                        "Failed to broadcast stock/price update after ingredient %s unit change",
                        ingrediente_id,
                    )

            uow.ingredientes.update(db_ingrediente)
            result = db_ingrediente

        # Propagate price change to all products if precio_actual was updated
        if 'precio_actual' in data.model_dump(exclude_unset=True):
            ProductoService.recalcular_precio_productos_afectados(session, ingrediente_id)
            # ── AFTER commit: broadcast price updates to affected products ──
            try:
                if ws_manager is None:
                    ws_manager = get_ws_manager()
                if ws_manager is not None:
                    from app.modules.CatalogoDeProductos.stock_ws_router import (
                        broadcast_price_update_for_products,
                    )
                    with CatalogoDeProductosUnitOfWork(session) as uow_p:
                        producto_ids = uow_p.productos.get_productos_afectados_por_ingrediente(ingrediente_id)
                    if producto_ids:
                        broadcast_price_update_for_products(
                            session, producto_ids, ws_manager,
                            motivo="ingrediente_precio_actualizado",
                        )
            except Exception:
                logger.exception(
                    "Failed to broadcast price update after ingredient %s price change via update()",
                    ingrediente_id,
                )
        # Refresh after commit to load auto-generated timestamps without discarding changes
        session.refresh(result)

        # ── AFTER commit: broadcast if stock changed ──
        if old_stock != new_stock:
            if ws_manager is None:
                ws_manager = get_ws_manager()
            if ws_manager is not None:
                from app.core.dependencies import fire_broadcast
                payload = {
                    "event": "stock_actualizado",
                    "entidad_tipo": "ingrediente",
                    "entidad_id": result.id,
                    "entidad_nombre": result.nombre,
                    "stock_anterior": old_stock,
                    "stock_nuevo": new_stock,
                    "motivo": "actualizacion",
                    "usuario_id": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                fire_broadcast(ws_manager, "stock_admin", payload)

        return result

    @staticmethod
    def soft_delete(session: Session, ingrediente_id: int, ws_manager=None) -> bool:
        """Soft-delete an ingredient. Returns True if deleted, False if not found.

        M2 (fix-stock-reconciliation): Blocks soft-delete if the ingredient is
        referenced by any active (non-deleted) product via ProductoIngrediente.
        """
        with CatalogoDeProductosUnitOfWork(session) as uow:
            db_ingrediente = uow.ingredientes.get_by_id(ingrediente_id)
            if not db_ingrediente:
                return False

            old_stock = db_ingrediente.stock_actual

            # M2: Check if ingredient is used by any active product
            stmt = select(ProductoIngrediente).join(
                Producto, ProductoIngrediente.producto_id == Producto.id,
            ).where(
                ProductoIngrediente.ingrediente_id == ingrediente_id,
                Producto.deleted_at.is_(None),
            )
            active_ref = session.exec(stmt).first()
            if active_ref:
                raise HTTPException(
                    status_code=409,
                    detail="No se puede eliminar: el ingrediente esta en uso por productos activos",
                )

            # ── Stock audit: log soft_delete ──
            HistorialStockService.registrar_cambio(
                uow,
                entidad_tipo="ingrediente",
                entidad_id=ingrediente_id,
                stock_anterior=old_stock,
                stock_nuevo=old_stock,
                motivo="soft_delete",
            )

            db_ingrediente.deleted_at = get_utc_now()
            uow.ingredientes.update(db_ingrediente)
            result = True
            result_nombre = db_ingrediente.nombre

        # ── AFTER commit: broadcast ──
        if ws_manager is None:
            ws_manager = get_ws_manager()
        if ws_manager is not None and result:
            from app.core.dependencies import fire_broadcast
            payload = {
                "event": "stock_actualizado",
                "entidad_tipo": "ingrediente",
                "entidad_id": ingrediente_id,
                "entidad_nombre": result_nombre,
                "stock_anterior": old_stock,
                "stock_nuevo": old_stock,
                "motivo": "soft_delete",
                "usuario_id": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            fire_broadcast(ws_manager, "stock_admin", payload)

        return result
