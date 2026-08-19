"""
Pedido service — the core business logic module for orders.

This is the most important file in the Sales module. It contains:
    - Order creation with detail snapshots
    - Finite State Machine (FSM) for state transitions
    - Ingredient stock deduction at order confirmation (make-to-order model)
    - Total calculation (subtotal, descuento, costo_envio, total)
    - Pre-creation stock validation (derived from ingredient availability)
    - Cancelation with role-based permissions and ingredient stock restoration
    - Append-only state change history

BUSINESS MODEL: make-to-order. Product stock is derived from ingredient
availability. Ingredients are consumed at order confirmation time
(PedidoService), NOT at manufacturing time (ProductoService).
es_producto_terminado products use stock_manual instead.

PATTERN: Unit of Work (UoW)
    ALL operations (read and write) go through VentasPagosTrazabilidadUnitOfWork.
"""
import logging
from datetime import datetime
from sqlmodel import Session
from typing import List, Optional
from decimal import Decimal
from fastapi import HTTPException, status
from app.core.routing import get_or_404
from .models import Pedido
from .schemas import PedidoRead

logger = logging.getLogger(__name__)
from .repository import SORTABLE_FIELDS
from .schemas import PedidoCreate, PedidoUpdate, ValidarStockInput, ValidarStockResponse, ValidarStockDetalleResponse, ValidarStockIngredienteResponse, StockItemResponse, DisponibilidadInput, DisponibilidadResponse, ProductoDisponibilidad, ProductoLimitante
from app.core.paginated_response import PaginatedResponse
from ..uow import VentasPagosTrazabilidadUnitOfWork
from app.modules.CatalogoDeProductos.uow import CatalogoDeProductosUnitOfWork
from app.modules.IdentidadYAcceso.uow import IdentidadYAccesoUnitOfWork
from app.modules.IdentidadYAcceso.DireccionEntrega.models import DireccionEntrega
from ..HistorialEstadoPedido.service import HistorialEstadoPedidoService
from ..DetallePedido.models import DetallePedido
from ..HistorialEstadoPedido.models import HistorialEstadoPedido
from app.core.base import get_utc_now
from app.core.dependencies import fire_broadcast, fire_broadcast_admin, fire_broadcast_user
from app.modules.CatalogoDeProductos.HistorialStock.service import HistorialStockService

# ---------------------------------------------------------------------------
# FINITE STATE MACHINE (FSM) definition
# ---------------------------------------------------------------------------
# Full flow:
#
#   PENDIENTE --[confirm]--> CONFIRMADO --[start prep]--> EN_PREP --[deliver]--> ENTREGADO
#       |                        |                        |
#       |  (customer/admin)      +--[cancel]--------------+
#       |                                                     (ADMIN/PEDIDOS)
#       +--[cancel]------------> CANCELADO <--[cancel]--------+
#
# Terminal states (no further transitions allowed):
#   - ENTREGADO: delivery completed
#   - CANCELADO: order cancelled
#
# State transition rules:
#   - Only one state advance at a time
#   - From PENDIENTE, CONFIRMADO, or EN_PREP: ADMIN/PEDIDOS can cancel
#   - From PENDIENTE or CONFIRMADO: CLIENT can also cancel (frontend-enforced)
#   - ENTREGADO and CANCELADO are TERMINAL — no coming back
# ---------------------------------------------------------------------------
ESTADOS_TERMINALES = {"ENTREGADO", "CANCELADO"}

# Payment methods that only allow in-store pickup (no delivery)
PICKUP_ONLY_METHODS = {"PAGO_LOCAL"}

TRANSICIONES_VALIDAS: dict[str, str] = {
    "PENDIENTE": "CONFIRMADO",
    "CONFIRMADO": "EN_PREP",
    "EN_PREP": "ENTREGADO",
}


class PedidoService:
    """Business logic for the Order entity — FSM, stock validation, and CRUD."""

    @staticmethod
    def _registrar_transicion(uow, pedido, estado_anterior, estado_siguiente, usuario_id=None, motivo=None):
        """Register an atomic state transition: INSERT audit trail + UPDATE order state.

        This is the ONLY place where HistorialEstadoPedido rows are created and where pedido.estado_codigo is modified. 
        Both operations happen within the same UoW transaction to ensure atomicity.

        Args:
            uow: Active VentasPagosTrazabilidadUnitOfWork instance.
            pedido: The Pedido ORM instance to transition.
            estado_anterior: Previous state (None = creation event).
            estado_siguiente: Target state string (e.g. 'CONFIRMADO', 'CANCELADO').
            usuario_id: Who triggered the transition (None = system/webhook).
            motivo: Optional reason string (e.g. "Cancelado por usuario").
        """
        # Insert audit trail row (append-only — nunca se modifica después de creado)
        uow.add(HistorialEstadoPedido(
            pedido_id=pedido.id,
            estado_desde=estado_anterior,
            estado_hacia=estado_siguiente,
            usuario_id=usuario_id,
            motivo=motivo,
            es_sistema=(usuario_id is None),
        ))
        # Update the order's current state
        pedido.estado_codigo = estado_siguiente
        uow.pedidos.update(pedido)

    @staticmethod
    def _validar_personalizacion(session: Session, producto_id: int, personalizacion: list[int]):
        """
        Validate that every ID in personalizacion belongs to a ProductoIngrediente
        with es_removible=True for the given producto_id.

        Raises HTTPException(422) if any ID is invalid or not removable.
        """
        if not personalizacion:
            return

        repo = CatalogoDeProductosUnitOfWork(session).productos
        ingredientes_asignados = repo.get_ingredientes(producto_id)

        # Build a set of valid removable ingredient IDs for this product
        # NOTE: get_ingredientes() returns list of dicts, not ORM objects
        ids_removibles = {
            ing["ingrediente_id"]
            for ing in ingredientes_asignados
            if ing["es_removible"]
        }

        invalid_ids = [i for i in personalizacion if i not in ids_removibles]
        if invalid_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "IDs de ingredientes invalidos o no removibles para el producto",
                    "producto_id": producto_id,
                    "invalid_ids": invalid_ids,
                }
            )

    @staticmethod
    def _aggregate_ingredient_requirements(uow, session, detalles) -> dict[int, Decimal]:
        """Aggregate ingredient requirements across a list of order/detail items.

        Each item must expose `producto_id` and `cantidad` (DetallePedido rows
        or ValidarStockDetalleInput schemas). Regular products contribute their
        recipe (converted to the ingredient's own unit) multiplied by quantity.
        es_producto_terminado products are skipped (they use stock_manual).

        Returns {ingrediente_id: total_required_quantity}.
        """
        from app.modules.CatalogoDeProductos.utils import convertir_cantidad, load_conversion_factors

        factores = load_conversion_factors(session)
        requirements: dict[int, Decimal] = {}
        for det in detalles:
            prod = uow.pedidos.get_producto(det.producto_id)
            if not prod or prod.es_producto_terminado:
                continue
            pi_ing_pairs = uow.pedidos.get_producto_with_ingredients(det.producto_id)
            for pi, ing in pi_ing_pairs:
                per_unit = convertir_cantidad(
                    Decimal(pi.cantidad),
                    pi.unidad_medida_id,
                    ing.unidad_medida_id,
                    factores=factores,
                )
                total = per_unit * Decimal(det.cantidad)
                requirements[pi.ingrediente_id] = (
                    requirements.get(pi.ingrediente_id, Decimal('0')) + total
                )
        return requirements

    @staticmethod
    def _deduct_stock_for_order(uow, pedido, session, usuario_id=None) -> list[dict]:
        """Deduct ingredient stock for all items in an order (make-to-order).

        Two-pass atomic pattern:
        1. Collect: aggregate ingredient requirements across all order details
        2. Lock: SELECT FOR UPDATE on ingredient rows (ORDER BY id ASC)
        3. Validate: check ALL ingredients have sufficient stock
        4. Deduct: subtract from ingredient stock + log HistorialStock

        Products with es_producto_terminado=True deduct from stock_manual
        instead (no ingredient associations).

        Returns list of stock_changes dicts for WebSocket broadcast.

        Raises HTTPException(409) with structured shortage details if any
        ingredient has insufficient stock.
        """
        stock_deductions: list[dict] = []

        # ── Step 1: Collect terminado products + aggregate ingredient requirements ──
        productos_terminados: list[dict] = []  # [{producto, detalle, old_stock}]

        for det in pedido.detalles:
            prod = uow.pedidos.get_producto(det.producto_id)
            if not prod:
                continue

            # ── es_producto_terminado: deduct from stock_manual ──
            if prod.es_producto_terminado:
                old_stock = prod.stock_manual or 0
                if old_stock < det.cantidad:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "stock_insuficiente",
                            "mensaje": f"Stock insuficiente de producto terminado '{prod.nombre}'",
                            "detalles": [{
                                "producto_id": det.producto_id,
                                "nombre_producto": det.nombre_snapshot,
                                "cantidad_solicitada": det.cantidad,
                                "stock_disponible": old_stock,
                            }],
                        },
                    )
                productos_terminados.append({
                    "producto": prod,
                    "detalle": det,
                    "old_stock": old_stock,
                })

        ingredient_deductions = PedidoService._aggregate_ingredient_requirements(
            uow, session, pedido.detalles
        )

        # ── Step 2: Lock ingredient rows (ordered by ID ASC for deadlock prevention) ──
        ingredient_ids = sorted(ingredient_deductions.keys())
        locked_ingredients = uow.pedidos.lock_ingredients_for_order(ingredient_ids)

        # ── Step 3: Validate ALL ingredients (collect every shortage) ──
        shortages: list[dict] = []
        for ing in locked_ingredients:
            needed = ingredient_deductions.get(ing.id, Decimal('0'))
            if ing.stock_actual < needed:
                shortages.append({
                    "ingrediente_id": ing.id,
                    "ingrediente_nombre": ing.nombre,
                    "cantidad_solicitada": int(needed),
                    "stock_disponible": ing.stock_actual,
                })

        if shortages:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "stock_insuficiente",
                    "mensaje": "Stock insuficiente de ingredientes para confirmar el pedido.",
                    "detalles": shortages,
                },
            )

        # ── Step 4: Deduct ALL ingredients ──
        for ing in locked_ingredients:
            needed = ingredient_deductions[ing.id]
            old_stock = ing.stock_actual
            ing.stock_actual -= int(needed)
            uow.add(ing)

            stock_deductions.append({
                "ingrediente_id": ing.id,
                "nombre": ing.nombre,
                "stock_anterior": old_stock,
                "stock_nuevo": ing.stock_actual,
                "cantidad_deducida": int(needed),
            })

            # ── Stock audit: log venta for ingredient ──
            HistorialStockService.registrar_cambio(
                uow,
                entidad_tipo="ingrediente",
                entidad_id=ing.id,
                stock_anterior=old_stock,
                stock_nuevo=ing.stock_actual,
                motivo="venta",
                usuario_id=usuario_id,
            )

        # ── Step 5: Deduct producto terminado stock_manual ──
        for pt_entry in productos_terminados:
            prod = pt_entry["producto"]
            det = pt_entry["detalle"]
            old_stock = pt_entry["old_stock"]
            prod.stock_manual = old_stock - det.cantidad
            uow.add(prod)

            stock_deductions.append({
                "producto_id": prod.id,
                "nombre": det.nombre_snapshot,
                "stock_anterior": old_stock,
                "stock_nuevo": prod.stock_manual,
                "cantidad_deducida": det.cantidad,
            })

            # ── Stock audit: log venta for producto terminado ──
            HistorialStockService.registrar_cambio(
                uow,
                entidad_tipo="producto",
                entidad_id=prod.id,
                stock_anterior=old_stock,
                stock_nuevo=prod.stock_manual,
                motivo="venta",
                usuario_id=usuario_id,
            )

        return stock_deductions

    @staticmethod
    def _restore_stock_for_order(uow, pedido, session, usuario_id=None) -> list[dict]:
        """Restore ingredient stock when an order is cancelled (make-to-order).

        Reverses the deduction done at order confirmation. For regular
        products, restores ingredient stock. For es_producto_terminado
        products, restores stock_manual.

        Returns list of stock_changes dicts for WebSocket broadcast.
        """
        from decimal import Decimal
        from app.modules.CatalogoDeProductos.utils import convertir_cantidad, load_conversion_factors

        factores = load_conversion_factors(session)
        stock_changes: list[dict] = []

        for det in pedido.detalles:
            prod = uow.pedidos.get_producto(det.producto_id)
            if not prod:
                continue

            # ── es_producto_terminado: restore stock_manual ──
            if prod.es_producto_terminado:
                old_stock = prod.stock_manual or 0
                prod.stock_manual = old_stock + det.cantidad
                uow.add(prod)
                stock_changes.append({
                    "producto_id": det.producto_id,
                    "nombre": det.nombre_snapshot,
                    "stock_anterior": old_stock,
                    "stock_nuevo": prod.stock_manual,
                    "cantidad_restaurada": det.cantidad,
                })
                HistorialStockService.registrar_cambio(
                    uow,
                    entidad_tipo="producto",
                    entidad_id=det.producto_id,
                    stock_anterior=old_stock,
                    stock_nuevo=prod.stock_manual,
                    motivo="cancelacion",
                    usuario_id=usuario_id,
                )
                continue

            # ── Regular product: restore ingredient stock ──
            pi_ing_pairs = uow.pedidos.get_producto_with_ingredients(det.producto_id)
            for pi, ing in pi_ing_pairs:
                per_unit = convertir_cantidad(
                    Decimal(pi.cantidad),
                    pi.unidad_medida_id,
                    ing.unidad_medida_id,
                    factores=factores,
                )
                total = per_unit * Decimal(det.cantidad)

                old_stock = ing.stock_actual
                ing.stock_actual += int(total)
                uow.add(ing)

                stock_changes.append({
                    "ingrediente_id": ing.id,
                    "nombre": ing.nombre,
                    "stock_anterior": old_stock,
                    "stock_nuevo": ing.stock_actual,
                    "cantidad_restaurada": int(total),
                })

                HistorialStockService.registrar_cambio(
                    uow,
                    entidad_tipo="ingrediente",
                    entidad_id=ing.id,
                    stock_anterior=old_stock,
                    stock_nuevo=ing.stock_actual,
                    motivo="cancelacion",
                    usuario_id=usuario_id,
                )

        return stock_changes

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100) -> PaginatedResponse[PedidoRead]:
        """List ALL orders with pagination. Intended for ADMIN/PEDIDOS users."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            rows = uow.pedidos.get_all_eager(skip=skip, limit=limit)
            total = uow.pedidos.count_all()
            return PaginatedResponse(
                items=[PedidoRead.model_validate(r) for r in rows],
                total=total,
                skip=skip,
                limit=limit,
            )

    @staticmethod
    def get_by_id(session: Session, pedido_id: int) -> Optional[Pedido]:
        """Fetch a single order by its primary key with eager-loaded details."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.pedidos.get_by_id_eager(pedido_id)

    @staticmethod
    def get_by_id_scoped(session: Session, pedido_id: int, user) -> Pedido:
        """Fetch a single order with ownership enforcement.

        ADMIN/PEDIDOS can see any order; regular users can only see their own.
        Raises HTTPException(404) if not found, HTTPException(403) if unauthorized.
        """
        pedido = PedidoService.get_by_id(session, pedido_id)
        pedido = get_or_404(pedido, "Pedido no encontrado")
        es_gestor = any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in user.roles)
        if not es_gestor and pedido.usuario_id != user.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este pedido")
        return pedido

    @staticmethod
    def get_by_usuario_id(session: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> PaginatedResponse[PedidoRead]:
        """Fetch non-deleted orders for a specific user, newest first."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            rows = uow.pedidos.get_by_usuario_id_eager(usuario_id, skip=skip, limit=limit)
            total = uow.pedidos.count_by_usuario_id(usuario_id)
            return PaginatedResponse(
                items=[PedidoRead.model_validate(r) for r in rows],
                total=total,
                skip=skip,
                limit=limit,
            )

    @staticmethod
    def get_activos(session: Session, skip: int = 0, limit: int = 100,
                    sort_by: str = "id", sort_order: str = "desc",
                    search: Optional[str] = None) -> PaginatedResponse[PedidoRead]:
        """Fetch non-terminal orders (not ENTREGADO or CANCELADO), with dynamic sorting and optional text search.

        Used for the "active orders" dashboard.
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            rows = uow.pedidos.get_activos(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search)
            total = uow.pedidos.count_activos(search=search)
            return PaginatedResponse(
                items=[PedidoRead.model_validate(r) for r in rows],
                total=total,
                skip=skip,
                limit=limit,
            )

    @staticmethod
    def get_activos_scoped(session: Session, user, skip: int = 0, limit: int = 100,
                           sort_by: str = "id", sort_order: str = "desc",
                           search: Optional[str] = None) -> PaginatedResponse[PedidoRead]:
        """Fetch active orders scoped to the user's role, with optional text search.

        ADMIN/PEDIDOS see all active orders; regular users only see their own.
        Sort validation is done here so the router stays thin.
        """
        if sort_by not in SORTABLE_FIELDS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"sort_by debe ser uno de: {', '.join(sorted(SORTABLE_FIELDS))}",
            )
        if sort_order not in ("asc", "desc"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="sort_order debe ser 'asc' o 'desc'",
            )

        es_gestor = any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in user.roles)
        if es_gestor:
            return PedidoService.get_activos(session, skip=skip, limit=limit,
                                             sort_by=sort_by, sort_order=sort_order,
                                             search=search)
        # Regular user: filter to their own active orders
        todos_activos = PedidoService.get_activos(session, skip=0, limit=10000,
                                                   sort_by=sort_by, sort_order=sort_order,
                                                   search=search)
        items_filtrados = [p for p in todos_activos.items if p.usuario_id == user.id]
        return PaginatedResponse(
            items=items_filtrados[skip:skip + limit],
            total=len(items_filtrados),
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_historial(session: Session, skip: int = 0, limit: int = 100,
                      sort_by: str = "id", sort_order: str = "desc",
                      search: Optional[str] = None) -> PaginatedResponse[PedidoRead]:
        """Fetch terminal-state orders (ENTREGADO or CANCELADO), with dynamic sorting and optional text search.

        Used for the order history view.
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            rows = uow.pedidos.get_historial(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search)
            total = uow.pedidos.count_historial(search=search)
            return PaginatedResponse(
                items=[PedidoRead.model_validate(r) for r in rows],
                total=total,
                skip=skip,
                limit=limit,
            )

    @staticmethod
    def get_historial_by_usuario(session: Session, usuario_id: int, skip: int = 0, limit: int = 100,
                                 search: Optional[str] = None) -> PaginatedResponse[PedidoRead]:
        """Fetch terminal-state orders for a specific user, most recently updated first, with optional text search."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            rows = uow.pedidos.get_historial_by_usuario(usuario_id, skip=skip, limit=limit, search=search)
            total = uow.pedidos.count_by_usuario_id(usuario_id, search=search)
            return PaginatedResponse(
                items=[PedidoRead.model_validate(r) for r in rows],
                total=total,
                skip=skip,
                limit=limit,
            )

    @staticmethod
    def get_historial_scoped(session: Session, pedido_id: int, user):
        """Return full state history for an order with ownership enforcement.

        ADMIN/PEDIDOS can see any order's history; regular users can only see their own.
        Delegates the actual history retrieval to HistorialEstadoPedidoService internally.
        """
        pedido = PedidoService.get_by_id(session, pedido_id)
        pedido = get_or_404(pedido, "Pedido no encontrado")
        es_gestor = any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in user.roles)
        if not es_gestor and pedido.usuario_id != user.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este pedido")
        return HistorialEstadoPedidoService.get_by_pedido(session, pedido_id)

    @staticmethod
    def create(session: Session, data: PedidoCreate, ws_manager=None) -> Pedido:
        """Create a new order with full integrity checks.

        Step-by-step logic:
        1. Auto-select the user's primary delivery address if none specified
        2. Load the address and capture direccion_snapshot
        3. Validate stock for ALL products BEFORE inserting anything
        4. Calculate subtotal and total on the server from detail snapshots
        5. Create the Pedido row with estado_codigo = "PENDIENTE"
        6. Create DetallePedido rows with price/name snapshots
        7. Register the creation event in HistorialEstadoPedido (estado_desde=NULL)
        8. After commit: broadcast to admin room

        Atomicity: everything happens inside a single UoW. If any step fails
        (stock validation, ingredient validation, DB constraint), the entire
        transaction is rolled back. No partial orders.
        """
        # ── Pickup-only payment methods: PAGO_LOCAL does NOT support delivery ──
        if data.forma_pago_codigo in PICKUP_ONLY_METHODS:
            if data.direccion_id is not None:
                # Allow if it references a company store (local), not a personal delivery address
                direccion = session.get(DireccionEntrega, data.direccion_id)
                if not direccion or not direccion.es_local:
                    raise HTTPException(
                        status_code=422,
                        detail="Este metodo de pago no admite envio a domicilio. Solo se permite seleccionar un local para retiro.",
                    )

        # Auto-select user's primary address if none provided
        # (skip for pickup-only methods: they don't need a delivery address)
        if data.direccion_id is None and data.forma_pago_codigo not in PICKUP_ONLY_METHODS:
            direccion_repo = IdentidadYAccesoUnitOfWork(session).direcciones
            principal = direccion_repo.get_principal(data.usuario_id)
            if principal:
                data.direccion_id = principal.id

        # Load address and create snapshot BEFORE the transaction
        direccion_snapshot = None
        if data.direccion_id is not None:
            direccion_repo = IdentidadYAccesoUnitOfWork(session).direcciones
            direccion = direccion_repo.get_by_id(data.direccion_id)
            if direccion:
                direccion_snapshot = {
                    "linea1": getattr(direccion, "linea1", None),
                    "linea2": getattr(direccion, "linea2", None),
                    "ciudad": getattr(direccion, "ciudad", None),
                }

        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            # Force costo_envio=0 for pickup-only payment methods
            if data.forma_pago_codigo in PICKUP_ONLY_METHODS:
                data.costo_envio = Decimal('0.00')

            costo_envio = data.costo_envio if data.direccion_id else Decimal('0.00')

            # ── Step 1: Pre-validate stock for ALL products ──
            producto_repo = CatalogoDeProductosUnitOfWork(session).productos
            if data.detalles:
                for det in data.detalles:
                    producto = producto_repo.get_by_id(det.producto_id)
                    get_or_404(producto, f"Producto ID {det.producto_id} no encontrado")

                    # Compute derived stock (make-to-order) or stock_manual
                    if producto.es_producto_terminado:
                        stock_disp = producto.stock_manual or 0
                    else:
                        stock_disp = producto_repo.compute_derived_stock(det.producto_id)
                        producto.stock_cantidad = stock_disp
                        uow.add(producto)

                    if stock_disp < det.cantidad:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={
                                "error": "stock_insuficiente",
                                "mensaje": f"Stock insuficiente para '{producto.nombre}'",
                                "producto_id": det.producto_id,
                                "solicitado": det.cantidad,
                                "disponible": stock_disp,
                            },
                        )

                    # Validate ingredient exclusions
                    if det.personalizacion:
                        PedidoService._validar_personalizacion(session, det.producto_id, det.personalizacion)

            # ── Step 2: Calculate totals server-side ──
            subtotal_calculado = Decimal('0')
            if data.detalles:
                for det in data.detalles:
                    subtotal_calculado += det.precio_snapshot * det.cantidad

            total = subtotal_calculado - data.descuento + costo_envio
            if total < 0:
                raise ValueError("El total no puede ser negativo")

            # ── Step 2: Create the Pedido ──
            db_pedido = Pedido(
                usuario_id=data.usuario_id,
                direccion_id=data.direccion_id,
                direccion_snapshot=direccion_snapshot,
                estado_codigo="PENDIENTE",
                forma_pago_codigo=data.forma_pago_codigo,
                subtotal=subtotal_calculado,
                descuento=data.descuento,
                costo_envio=costo_envio,
                total=total,
                notas=data.notas,
            )
            uow.pedidos.create(db_pedido)

            # ── Step 4: Create DetallePedido rows ──
            if data.detalles:
                for det in data.detalles:
                    line_total = det.precio_snapshot * det.cantidad
                    uow.add(DetallePedido(
                        pedido_id=db_pedido.id,
                        producto_id=det.producto_id,
                        cantidad=det.cantidad,
                        nombre_snapshot=det.nombre_snapshot,
                        precio_snapshot=det.precio_snapshot,
                        subtotal_snap=line_total,
                        personalizacion=det.personalizacion,
                    ))

            # ── Step 5: Register creation in history ──
            PedidoService._registrar_transicion(
                uow,
                pedido=db_pedido,
                estado_anterior=None,
                estado_siguiente="PENDIENTE",
                usuario_id=data.usuario_id,
            )

            uow.refresh(db_pedido)
            result_pedido = db_pedido

        # ── AFTER UoW commit: broadcast new order to admin room ──
        if ws_manager is not None:
            payload = {
                "event": "estado_cambiado",
                "pedido_id": result_pedido.id,
                "estado_anterior": None,
                "estado_nuevo": "PENDIENTE",
                "usuario_id": data.usuario_id,
                "motivo": None,
                "timestamp": datetime.utcnow().isoformat(),
            }
            fire_broadcast_admin(ws_manager, payload)

        # Auto-confirm PAGO_LOCAL orders (payment happens in person at the store)
        if data.forma_pago_codigo == "PAGO_LOCAL" and ws_manager is not None:
            class _SistemaUser:
                id = None
            PedidoService.avanzar_estado(session, result_pedido.id, _SistemaUser(), ws_manager=ws_manager)

        return result_pedido

    @staticmethod
    def validar_stock_items(session: Session, data: ValidarStockInput) -> ValidarStockResponse:
        """Validate stock availability WITHOUT creating an order or any side effects.

        This is a READ-ONLY check used by the frontend cart to show stock
        errors in real-time. Uses derived stock (make-to-order model) or
        stock_manual (for es_producto_terminado products). Also validates
        SHARED ingredient stock: the aggregate requirement across ALL items
        must not exceed each ingredient's stock.
        """
        from app.modules.CatalogoDeProductos.uow import CatalogoDeProductosUnitOfWork

        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            errores: list[ValidarStockDetalleResponse] = []
            ingredientes_errores: list[ValidarStockIngredienteResponse] = []
            items: list[StockItemResponse] = []
            producto_repo = CatalogoDeProductosUnitOfWork(session).productos

            for det in data.detalles:
                prod = uow.pedidos.get_producto(det.producto_id)
                if not prod:
                    raise HTTPException(status_code=404, detail=f"Producto {det.producto_id} no encontrado")

                # Compute derived stock or use stock_manual
                if prod.es_producto_terminado:
                    stock_disp = prod.stock_manual or 0
                else:
                    stock_disp = producto_repo.compute_derived_stock(det.producto_id)
                    prod.stock_cantidad = stock_disp
                    uow.add(prod)

                if stock_disp < det.cantidad:
                    errores.append(ValidarStockDetalleResponse(
                        producto_id=det.producto_id,
                        nombre_producto=prod.nombre,
                        cantidad_solicitada=det.cantidad,
                        stock_disponible=stock_disp,
                    ))

                # Always include stock info for every product
                items.append(StockItemResponse(
                    producto_id=det.producto_id,
                    nombre_producto=prod.nombre,
                    stock_disponible=stock_disp,
                ))

            # ── Shared-ingredient validation: aggregate requirements across all items ──
            requirements = PedidoService._aggregate_ingredient_requirements(
                uow, session, data.detalles
            )
            for ingrediente_id, needed in requirements.items():
                ing = uow.pedidos.get_ingrediente(ingrediente_id)
                if ing and ing.stock_actual < needed:
                    ingredientes_errores.append(ValidarStockIngredienteResponse(
                        ingrediente_id=ingrediente_id,
                        ingrediente_nombre=ing.nombre,
                        cantidad_solicitada=int(needed),
                        stock_disponible=ing.stock_actual,
                        unidad_medida_simbolo=ing.unidad_medida_simbolo,
                    ))

            return ValidarStockResponse(
                valido=len(errores) == 0 and len(ingredientes_errores) == 0,
                detalles=errores,
                ingredientes=ingredientes_errores,
                items=items,
            )

    @staticmethod
    def disponibilidad_productos(session: Session, data: DisponibilidadInput) -> DisponibilidadResponse:
        """Compute, for each requested product, how many more units can be added
        given the current cart contents (shared-ingredient aware).

        READ-ONLY: does NOT reserve or deduct stock. A product with `agregable=0`
        cannot currently be added to the cart without exceeding stock.
        """
        from app.modules.CatalogoDeProductos.uow import CatalogoDeProductosUnitOfWork
        from app.modules.CatalogoDeProductos.utils import convertir_cantidad, load_conversion_factors

        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            # Current cart ingredient consumption + per-product cart quantity
            cart_use = PedidoService._aggregate_ingredient_requirements(uow, session, data.carrito)
            cart_qty: dict[int, int] = {}
            for item in data.carrito:
                cart_qty[item.producto_id] = cart_qty.get(item.producto_id, 0) + item.cantidad

            # Cart product -> ingredient ids + name (for naming limitantes).
            cart_product_ingredients: dict[int, set[int]] = {}
            cart_product_nombres: dict[int, str] = {}
            for item in data.carrito:
                cprod = uow.pedidos.get_producto(item.producto_id)
                if not cprod:
                    continue
                cart_product_nombres[item.producto_id] = cprod.nombre
                if cprod.es_producto_terminado:
                    continue
                pairs = uow.pedidos.get_producto_with_ingredients(item.producto_id)
                cart_product_ingredients[item.producto_id] = {pi.ingrediente_id for pi, _ in pairs}

            factores = load_conversion_factors(session)
            result: list[ProductoDisponibilidad] = []

            for pid in data.productos:
                prod = uow.pedidos.get_producto(pid)
                if not prod:
                    result.append(ProductoDisponibilidad(producto_id=pid, agregable=0))
                    continue

                limitantes: list[ProductoLimitante] = []

                if prod.es_producto_terminado:
                    agregable = max(0, (prod.stock_manual or 0) - cart_qty.get(pid, 0))
                else:
                    pi_ing_pairs = uow.pedidos.get_producto_with_ingredients(pid)
                    agregable: Optional[int] = None
                    limitante_ing_ids: set[int] = set()
                    for pi, ing in pi_ing_pairs:
                        per_unit = convertir_cantidad(
                            Decimal(pi.cantidad),
                            pi.unidad_medida_id,
                            ing.unidad_medida_id,
                            factores=factores,
                        )
                        if per_unit <= 0:
                            continue
                        remaining = ing.stock_actual - cart_use.get(pi.ingrediente_id, Decimal('0'))
                        addable_for_ing = int(remaining // per_unit)
                        if addable_for_ing < 0:
                            addable_for_ing = 0
                        if agregable is None or addable_for_ing < agregable:
                            agregable = addable_for_ing
                            limitante_ing_ids = {pi.ingrediente_id}
                        elif addable_for_ing == agregable:
                            limitante_ing_ids.add(pi.ingrediente_id)
                    if agregable is None:
                        agregable = 0
                    limitantes = [
                        ProductoLimitante(producto_id=cid, nombre=cart_product_nombres[cid])
                        for cid, cing in cart_product_ingredients.items()
                        if cid != pid and (cing & limitante_ing_ids)
                    ]

                result.append(ProductoDisponibilidad(
                    producto_id=pid, agregable=int(agregable), limitantes=limitantes,
                ))

            return DisponibilidadResponse(productos=result)

    @staticmethod
    def actualizar_detalle(session: Session, pedido_id: int, producto_id: int, cantidad: int) -> Pedido:
        """Update or remove a detail line on a PENDIENTE order.

        cantidad=0 removes the detail line.
        Only works on PENDIENTE orders — once CONFIRMADO, details are frozen
        because stock has already been deducted.

        After modification, subtotal and total are recalculated from the
        remaining details' subtotal_snap values.
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id_eager(pedido_id)
            get_or_404(db_pedido, "Pedido no encontrado")
            if db_pedido.estado_codigo != "PENDIENTE":
                raise HTTPException(status_code=400, detail="Solo se pueden modificar detalles en pedidos PENDIENTE")

            detalle = uow.pedidos.get_detalle_by_producto(pedido_id, producto_id)
            get_or_404(detalle, "Detalle no encontrado en el pedido")

            if cantidad <= 0:
                uow.delete(detalle)
                uow.flush()  # Process deletion to avoid cascade issues on pedido update
                uow.session.expire(db_pedido, ['detalles'])  # Expire stale relationship
            else:
                # Validate stock BEFORE updating
                prod = uow.pedidos.get_producto(producto_id)
                if prod:
                    if prod.es_producto_terminado:
                        stock_disp = prod.stock_manual or 0
                    else:
                        producto_repo = CatalogoDeProductosUnitOfWork(session).productos
                        stock_disp = producto_repo.compute_derived_stock(producto_id)
                        prod.stock_cantidad = stock_disp
                        uow.add(prod)
                    if stock_disp < cantidad:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={
                                "error": "stock_insuficiente",
                                "mensaje": f"Stock insuficiente para '{prod.nombre}'",
                                "producto_id": producto_id,
                                "solicitado": cantidad,
                                "disponible": stock_disp,
                            },
                        )
                detalle.cantidad = cantidad
                detalle.subtotal_snap = detalle.precio_snapshot * cantidad
                uow.detalles.update(detalle)

            # Recalculate order totals from remaining details
            detalles_restantes = uow.pedidos.get_detalles(pedido_id)
            nuevo_subtotal = sum(d.subtotal_snap for d in detalles_restantes)
            db_pedido.subtotal = nuevo_subtotal
            db_pedido.total = nuevo_subtotal - db_pedido.descuento + (db_pedido.costo_envio or Decimal('0.00'))
            if db_pedido.total < 0:
                db_pedido.total = Decimal('0.00')
            uow.pedidos.update(db_pedido)
            uow.refresh(db_pedido)
            return db_pedido

    @staticmethod
    def avanzar_estado(session: Session, pedido_id: int, usuario, ws_manager=None) -> tuple[Pedido, str]:
        """Advance the order to the next FSM state.

        This is the CORE state transition method. Flow:
        1. Fetch the order, validate it exists
        2. Check it's not in a terminal state
        3. Look up the next state from TRANSICIONES_VALIDAS
        4. If transitioning to CONFIRMADO and NOT MERCADOPAGO:
            a. Validate product stock sufficiency (with SELECT FOR UPDATE lock)
            b. Deduct product stock (stock_cantidad -= cantidad)
            (MercadoPago orders are blocked here — they go through the IPN webhook)
        5. Register the change in HistorialEstadoPedido (append-only)
        6. Broadcast to pedido room + admin room AFTER UoW commit
        7. Return (pedido, estado_anterior)

        Under the make-to-stock model, only finished-goods inventory is deducted.
        Ingredients are consumed at manufacturing time (ProductoService).

        IMPORTANT: The result is computed inside the UoW block, committed via
        __exit__, and the broadcast happens OUTSIDE the block. This ensures
        clients are only notified after the transaction is durable.
        """
        usuario_id = usuario.id if hasattr(usuario, 'id') else None

        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            get_or_404(db_pedido, "Pedido no encontrado")

            estado_anterior = db_pedido.estado_codigo
            if estado_anterior in ESTADOS_TERMINALES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El pedido ya está en estado terminal '{estado_anterior}'",
                )

            if estado_anterior not in TRANSICIONES_VALIDAS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No hay transición definida desde '{estado_anterior}'",
                )

            estado_siguiente = TRANSICIONES_VALIDAS[estado_anterior]

            # PENDIENTE -> CONFIRMADO: allowed for non-MP payment methods (PAGO_LOCAL, TRANSFERENCIA)
            # MERCADOPAGO orders MUST go through the IPN webhook (PagoService.process_webhook)
            if estado_siguiente == "CONFIRMADO" and db_pedido.forma_pago_codigo == "MERCADOPAGO":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="La confirmacion del pedido con MercadoPago solo puede realizarse mediante pago aprobado",
                )

            # For non-MP PENDIENTE->CONFIRMADO: validate and deduct stock here.
            # For MercadoPago orders, the webhook blocks above and stock is handled
            # by confirmar_por_pago() called from PagoService.process_webhook().
            #
            # MAKE-TO-ORDER model: ingredient stock is deducted at order
            # confirmation time. Product stock is DERIVED from ingredient
            # availability, not stored in a writable column.
            stock_changes: list[dict] = []  # Track stock changes for audit + WS
            if estado_siguiente == "CONFIRMADO":
                stock_changes = PedidoService._deduct_stock_for_order(
                    uow, db_pedido, session, usuario_id,
                )

            # Atomic transition: audit trail + state update
            PedidoService._registrar_transicion(
                uow,
                pedido=db_pedido,
                estado_anterior=estado_anterior,
                estado_siguiente=estado_siguiente,
                usuario_id=usuario_id,
            )

            # Collect product IDs for derived stock broadcast (Phase 3)
            result_producto_ids: list[int] = []
            if estado_siguiente == "CONFIRMADO":
                try:
                    result_producto_ids = [det.producto_id for det in db_pedido.detalles]
                except Exception:
                    result_producto_ids = []

            # ── Phase 3: Broadcast derived stock for affected products (INSIDE UoW) ──
            if result_producto_ids and ws_manager is not None:
                from app.modules.CatalogoDeProductos.stock_ws_router import (
                    broadcast_derived_stock_for_products,
                )
                broadcast_derived_stock_for_products(
                    session, result_producto_ids, ws_manager, motivo="venta",
                )

            # Save results for use AFTER commit
            result_pedido = db_pedido
            result_estado_anterior = estado_anterior
            result_estado_siguiente = estado_siguiente

        # ── AFTER UoW commit: broadcast to WebSocket clients ──
        if ws_manager is not None:
            # 1. Broadcast order state change
            payload = {
                "event": "estado_cambiado",
                "pedido_id": result_pedido.id,
                "estado_anterior": result_estado_anterior,
                "estado_nuevo": result_estado_siguiente,
                "usuario_id": usuario_id,
                "motivo": None,
                "timestamp": datetime.utcnow().isoformat(),
            }
            fire_broadcast(ws_manager, result_pedido.id, payload)
            fire_broadcast_admin(ws_manager, payload)
            fire_broadcast_user(ws_manager, result_pedido.usuario_id, payload)

            # 2. Broadcast stock_actualizado for each affected ingredient and producto_terminado
            for sc in stock_changes:
                if "ingrediente_id" in sc:
                    stock_payload = {
                        "event": "stock_actualizado",
                        "entidad_tipo": "ingrediente",
                        "entidad_id": sc["ingrediente_id"],
                        "entidad_nombre": sc["nombre"],
                        "stock_anterior": sc["stock_anterior"],
                        "stock_nuevo": sc["stock_nuevo"],
                        "motivo": "venta",
                        "usuario_id": usuario_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    fire_broadcast(ws_manager, "stock_admin", stock_payload)
                elif "producto_id" in sc:
                    stock_payload = {
                        "event": "stock_actualizado",
                        "entidad_tipo": "producto",
                        "entidad_id": sc["producto_id"],
                        "entidad_nombre": sc["nombre"],
                        "stock_anterior": sc["stock_anterior"],
                        "stock_nuevo": sc["stock_nuevo"],
                        "motivo": "venta",
                        "usuario_id": usuario_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    fire_broadcast(ws_manager, f"producto_{sc['producto_id']}", stock_payload)
                    fire_broadcast(ws_manager, "stock_admin", stock_payload)

        return (result_pedido, result_estado_anterior)

    @staticmethod
    def crear_desde_snapshot(
        session: Session,
        snapshot,
        snapshot_repo=None,
        uow: VentasPagosTrazabilidadUnitOfWork | None = None,
    ) -> Pedido:
        """Create a complete Pedido from a carrito_snapshot after MP payment approval.

        This is the POST-PAGO creation path. The Pedido is created in CONFIRMADO
        state directly (bypassing PENDIENTE) because payment is already confirmed.

        Steps (all inside a single UoW):
        1. Validate product stock for all snapshot items
        2. Create Pedido in CONFIRMADO state with snapshot monetary data
        3. Create DetallePedido rows with name/price snapshots
        4. Deduct product stock
        5. Register creation in HistorialEstadoPedido (estado_desde=NULL)
        6. Delete the carrito_snapshot row atomically

        Under the make-to-stock model, only finished-goods inventory is deducted.
        Ingredients are consumed at manufacturing time (ProductoService).

        Atomicity: If any step fails, the entire UoW rolls back, preserving
        the snapshot for retry.

        Args:
            session: SQLModel database session.
            snapshot: CarritoSnapshot ORM instance.
            snapshot_repo: Optional CarritoSnapshotRepository (uses UoW's if None).
            uow: Optional VentasPagosTrazabilidadUnitOfWork. When provided, the
                method uses it directly and the CALLER owns the transaction
                boundary. When None (backward-compat), the method creates its
                own UoW internally.

        Returns:
            The newly created Pedido ORM instance.

        Raises:
            HTTPException(409): If stock is insufficient at creation time.
        """
        from ..CarritoSnapshot.repository import CarritoSnapshotRepository

        _owns_uow = uow is None

        def _create(
            uow_inner: VentasPagosTrazabilidadUnitOfWork,
        ) -> tuple[Pedido, list[dict], list[int]]:
            """Core creation logic shared between both paths.

            Returns:
                (pedido, stock_changes, snapshot_producto_ids)
            """
            # ── Step 1: Validate product existence ──
            producto_repo = CatalogoDeProductosUnitOfWork(session).productos
            for item_dict in snapshot.items:
                producto_id = item_dict.get("producto_id")
                producto = producto_repo.get_by_id(producto_id)
                if not producto:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "stock_insuficiente",
                            "mensaje": "Uno o mas productos del carrito ya no estan disponibles.",
                            "detalles": [{
                                "producto_id": producto_id,
                                "error": "producto_no_encontrado",
                            }],
                        },
                    )

            # ── Step 2: Create the Pedido ──
            db_pedido = Pedido(
                usuario_id=snapshot.usuario_id,
                direccion_id=snapshot.direccion_id,
                direccion_snapshot=snapshot.direccion_snapshot,
                estado_codigo="CONFIRMADO",
                forma_pago_codigo=snapshot.forma_pago_codigo,
                subtotal=snapshot.subtotal,
                descuento=Decimal("0.00"),
                costo_envio=snapshot.costo_envio,
                total=snapshot.total,
                notas=snapshot.notas,
            )

            uow_inner.pedidos.create(db_pedido)

            # ── Step 3: Create DetallePedido rows ──
            for item_dict in snapshot.items:
                producto_id = item_dict.get("producto_id")
                cantidad = item_dict.get("cantidad", 0)
                nombre = item_dict.get("nombre", "")
                precio = Decimal(str(item_dict.get("precio", "0.00")))
                ingredientes_excluidos = item_dict.get("ingredientes_excluidos") or []
                line_total = precio * cantidad

                uow_inner.add(DetallePedido(
                    pedido_id=db_pedido.id,
                    producto_id=producto_id,
                    cantidad=cantidad,
                    nombre_snapshot=nombre,
                    precio_snapshot=precio,
                    subtotal_snap=line_total,
                    personalizacion=ingredientes_excluidos if ingredientes_excluidos else None,
                ))

            # ── Step 4: Deduct ingredient stock + audit (make-to-order) ──
            stock_changes_out: list[dict] = PedidoService._deduct_stock_for_order(
                uow_inner, db_pedido, session, usuario_id=None,
            )

            # Collect product IDs for derived stock broadcast (Phase 3)
            snapshot_producto_ids_out: list[int] = []
            try:
                snapshot_producto_ids_out = [det.producto_id for det in db_pedido.detalles]
            except Exception:
                snapshot_producto_ids_out = []

            # ── Step 5: Register creation in history ──
            PedidoService._registrar_transicion(
                uow_inner,
                pedido=db_pedido,
                estado_anterior=None,
                estado_siguiente="CONFIRMADO",
                usuario_id=None,  # System — triggered by webhook
            )

            # ── Step 6: Delete the snapshot atomically ──
            # Need to reload snapshot in this UoW's session
            snapshot_to_delete = uow_inner.snapshots.get_by_external_reference(
                snapshot.external_reference
            )
            if snapshot_to_delete:
                uow_inner.snapshots.delete(snapshot_to_delete)

            # ── Phase 3: Broadcast derived stock for affected products (INSIDE UoW) ──
            if snapshot_producto_ids_out:
                from app.modules.CatalogoDeProductos.stock_ws_router import (
                    broadcast_derived_stock_for_products,
                )
                from app.core.dependencies import get_ws_manager as _get_ws_inner
                ws_inner = _get_ws_inner()
                if ws_inner is not None:
                    broadcast_derived_stock_for_products(
                        session, snapshot_producto_ids_out, ws_inner, motivo="venta",
                    )

            uow_inner.refresh(db_pedido)
            return db_pedido, stock_changes_out, snapshot_producto_ids_out

        if _owns_uow:
            # Backward-compat: create internal UoW and handle post-commit broadcast
            with VentasPagosTrazabilidadUnitOfWork(session) as uow_inner:
                result_pedido_snap, stock_changes_snap, _snapshot_ids = _create(uow_inner)

            # ── AFTER UoW commit: broadcast ingredient/product stock changes ──
            from app.core.dependencies import get_ws_manager as _get_ws
            ws = _get_ws()
            if ws is not None and stock_changes_snap:
                for sc in stock_changes_snap:
                    if "ingrediente_id" in sc:
                        stock_payload = {
                            "event": "stock_actualizado",
                            "entidad_tipo": "ingrediente",
                            "entidad_id": sc["ingrediente_id"],
                            "entidad_nombre": sc["nombre"],
                            "stock_anterior": sc["stock_anterior"],
                            "stock_nuevo": sc["stock_nuevo"],
                            "motivo": "venta",
                            "usuario_id": None,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        fire_broadcast(ws, "stock_admin", stock_payload)
                    elif "producto_id" in sc:
                        stock_payload = {
                            "event": "stock_actualizado",
                            "entidad_tipo": "producto",
                            "entidad_id": sc["producto_id"],
                            "entidad_nombre": sc["nombre"],
                            "stock_anterior": sc["stock_anterior"],
                            "stock_nuevo": sc["stock_nuevo"],
                            "motivo": "venta",
                            "usuario_id": None,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        fire_broadcast(ws, f"producto_{sc['producto_id']}", stock_payload)
                        fire_broadcast(ws, "stock_admin", stock_payload)

            return result_pedido_snap
        else:
            # Caller-provided UoW: use it directly, caller owns commit + broadcast
            result_pedido, _sc, _ids = _create(uow)
            return result_pedido

    @staticmethod
    def confirmar_por_pago(session: Session, pedido_id: int) -> Pedido:
        """DEPRECATED: Advance PENDIENTE -> CONFIRMADO via payment webhook.

        This method is DEPRECATED for the MercadoPago flow. It is replaced by
        crear_desde_snapshot() which creates the Pedido directly in CONFIRMADO
        state instead of advancing from PENDIENTE.

        The method is kept for backward compatibility with tests and to serve
        as documentation of the original flow. It should NOT be called from
        process_webhook() anymore.

        Original docstring follows:

        Called by PagoService.process_webhook() when MercadoPago reports
        an approved payment. For MERCADOPAGO orders this is the ONLY way
        PENDIENTE advances to CONFIRMADO — the API endpoint blocks the
        MP transition in avanzar_estado.
        Non-MP methods (PAGO_LOCAL, TRANSFERENCIA) transition directly via
        avanzar_estado, which also validates/deducts stock.

        Flow:
        1. Validate the order exists and is PENDIENTE
        2. Validate product stock sufficiency
        3. Deduct product stock (stock_cantidad -= cantidad)
        4. Register the transition in HistorialEstadoPedido (append-only)
        5. Return the updated Pedido

        Under the make-to-stock model, only finished-goods inventory is deducted.
        Ingredients are consumed at manufacturing time (ProductoService).

        NOTE: Does NOT create a new MP payment — the Pago record already
        exists from init_mp_payment() called by the frontend.
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id_eager(pedido_id)
            get_or_404(db_pedido, "Pedido no encontrado")

            if db_pedido.estado_codigo != "PENDIENTE":
                logger.warning(
                    "confirmar_por_pago: pedido %s is %s, not PENDIENTE",
                    pedido_id, db_pedido.estado_codigo,
                )
                # Not an error — webhook may arrive after already confirmed
                return db_pedido

            # Stock validation + deduction — ingredient-level (make-to-order)
            _ = PedidoService._deduct_stock_for_order(
                uow, db_pedido, session, usuario_id=None,
            )

            # Register transition: PENDIENTE -> CONFIRMADO
            PedidoService._registrar_transicion(
                uow,
                pedido=db_pedido,
                estado_anterior="PENDIENTE",
                estado_siguiente="CONFIRMADO",
                usuario_id=None,  # System user — triggered by webhook
            )

            return db_pedido

    @staticmethod
    def cancelar_pedido(session: Session, pedido_id: int, usuario, motivo: str = "Cancelado por usuario", ws_manager=None) -> Pedido:
        """Cancel an order. Only PENDIENTE, CONFIRMADO, or EN_PREP orders can be cancelled.

        Permission rules:
            - Allowed states: PENDIENTE, CONFIRMADO, EN_PREP
            - Stock is restored if cancelling from CONFIRMADO or EN_PREP (previously deducted)
            - ENTREGADO and CANCELADO cannot be cancelled
            - Role restriction (AdminOrPedidos) is enforced at the router level

        Args:
            motivo: User-provided cancellation reason (replaces hardcoded string).
            ws_manager: Optional WSManager for broadcasting the cancellation event.
        """
        usuario_id = usuario.id if hasattr(usuario, 'id') else None

        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            get_or_404(db_pedido, "Pedido no encontrado")

            estado_actual = db_pedido.estado_codigo
            if estado_actual in ESTADOS_TERMINALES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El pedido ya está en estado terminal '{estado_actual}'",
                )

            # Only PENDIENTE, CONFIRMADO and EN_PREP can be cancelled
            estados_permitidos_cancelar = {"PENDIENTE", "CONFIRMADO", "EN_PREP"}
            if estado_actual not in estados_permitidos_cancelar:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No se puede cancelar un pedido en estado '{estado_actual}'",
                )

            # Restore stock if cancelling from CONFIRMADO or EN_PREP (stock was deducted at confirmation)
            stock_changes: list[dict] = []
            if estado_actual in ("CONFIRMADO", "EN_PREP"):
                stock_changes = PedidoService._restore_stock_for_order(
                    uow, db_pedido, session, usuario_id,
                )

            PedidoService._registrar_transicion(
                uow,
                pedido=db_pedido,
                estado_anterior=estado_actual,
                estado_siguiente="CANCELADO",
                usuario_id=usuario_id,
                motivo=motivo,
            )

            # Collect product IDs for derived stock broadcast (Phase 3)
            result_producto_ids: list[int] = []
            if estado_actual in ("CONFIRMADO", "EN_PREP"):
                try:
                    result_producto_ids = [det.producto_id for det in db_pedido.detalles]
                except Exception:
                    result_producto_ids = []

            # ── Phase 3: Broadcast derived stock for affected products (INSIDE UoW) ──
            if result_producto_ids and ws_manager is not None:
                from app.modules.CatalogoDeProductos.stock_ws_router import (
                    broadcast_derived_stock_for_products,
                )
                broadcast_derived_stock_for_products(
                    session, result_producto_ids, ws_manager, motivo="cancelacion",
                )

            # Save result for use AFTER commit
            result_pedido = db_pedido
            result_estado_anterior = estado_actual

        # ── AFTER UoW commit: broadcast to WebSocket clients ──
        if ws_manager is not None:
            payload = {
                "event": "pedido_cancelado",
                "pedido_id": result_pedido.id,
                "estado_anterior": result_estado_anterior,
                "estado_nuevo": "CANCELADO",
                "usuario_id": usuario_id,
                "motivo": motivo,
                "timestamp": datetime.utcnow().isoformat(),
            }
            fire_broadcast(ws_manager, result_pedido.id, payload)
            fire_broadcast_admin(ws_manager, payload)
            fire_broadcast_user(ws_manager, result_pedido.usuario_id, payload)

            # 2. Broadcast stock_actualizado for each restored ingredient or producto_terminado
            for sc in stock_changes:
                if "ingrediente_id" in sc:
                    stock_payload = {
                        "event": "stock_actualizado",
                        "entidad_tipo": "ingrediente",
                        "entidad_id": sc["ingrediente_id"],
                        "entidad_nombre": sc["nombre"],
                        "stock_anterior": sc["stock_anterior"],
                        "stock_nuevo": sc["stock_nuevo"],
                        "motivo": "cancelacion",
                        "usuario_id": usuario_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    fire_broadcast(ws_manager, "stock_admin", stock_payload)
                elif "producto_id" in sc:
                    stock_payload = {
                        "event": "stock_actualizado",
                        "entidad_tipo": "producto",
                        "entidad_id": sc["producto_id"],
                        "entidad_nombre": sc["nombre"],
                        "stock_anterior": sc["stock_anterior"],
                        "stock_nuevo": sc["stock_nuevo"],
                        "motivo": "cancelacion",
                        "usuario_id": usuario_id,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    fire_broadcast(ws_manager, f"producto_{sc['producto_id']}", stock_payload)
                    fire_broadcast(ws_manager, "stock_admin", stock_payload)

        return result_pedido

    @staticmethod
    def update(session: Session, pedido_id: int, data: PedidoUpdate) -> Optional[Pedido]:
        """Update order metadata and/or replace detail lines.

        Allowed for any authenticated user with ADMIN/PEDIDOS role.
        Only provided fields are applied (exclude_unset=True).
        Does NOT modify state — that has a dedicated endpoint.

        When `detalles` is provided:
        - Only works on PENDIENTE orders (stock already deducted for CONFIRMADO+)
        - ALL existing details are replaced with the new ones
        - Subtotal and total are recalculated from the new details' subtotal_snap
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            if not db_pedido:
                return None

            values = data.model_dump(exclude_unset=True)

            # Handle detail replacement (only for PENDIENTE orders)
            if 'detalles' in values:
                if db_pedido.estado_codigo != "PENDIENTE":
                    raise HTTPException(
                        status_code=400,
                        detail="Solo se pueden modificar los detalles de pedidos en estado PENDIENTE",
                    )

                # Remove all existing details
                for det in uow.pedidos.get_detalles(pedido_id):
                    uow.delete(det)

                # Add new details from the request
                nuevo_subtotal = Decimal('0')
                for det in data.detalles:
                    # Validate ingredient exclusions before creating the detail
                    if det.personalizacion:
                        PedidoService._validar_personalizacion(session, det.producto_id, det.personalizacion)

                    # Validate stock for this detail line
                    prod = uow.pedidos.get_producto(det.producto_id)
                    get_or_404(prod, f"Producto ID {det.producto_id} no encontrado")
                    if prod.es_producto_terminado:
                        stock_disp = prod.stock_manual or 0
                    else:
                        stock_disp = CatalogoDeProductosUnitOfWork(session).productos.compute_derived_stock(det.producto_id)
                    if stock_disp < det.cantidad:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail={
                                "error": "stock_insuficiente",
                                "mensaje": f"Stock insuficiente para '{prod.nombre}'",
                                "producto_id": det.producto_id,
                                "solicitado": det.cantidad,
                                "disponible": stock_disp,
                            },
                        )

                    line_total = det.precio_snapshot * det.cantidad
                    nuevo_subtotal += line_total
                    uow.add(DetallePedido(
                        pedido_id=pedido_id,
                        producto_id=det.producto_id,
                        cantidad=det.cantidad,
                        nombre_snapshot=det.nombre_snapshot,
                        precio_snapshot=det.precio_snapshot,
                        subtotal_snap=line_total,
                        personalizacion=det.personalizacion,
                    ))

                # Recalculate order totals
                db_pedido.subtotal = nuevo_subtotal
                db_pedido.total = nuevo_subtotal - db_pedido.descuento + (db_pedido.costo_envio or Decimal('0.00'))
                if db_pedido.total < 0:
                    db_pedido.total = Decimal('0.00')

                # Remove 'detalles' from values to avoid setattr on the field (not a column)
                del values['detalles']

            # Apply remaining metadata fields
            for key, value in values.items():
                setattr(db_pedido, key, value)

            uow.pedidos.update(db_pedido)
            uow.refresh(db_pedido)
            return db_pedido

    @staticmethod
    def soft_delete(session: Session, pedido_id: int) -> bool:
        """Soft-delete an order by setting deleted_at.

        The row remains in the database for reporting/historical purposes,
        but is excluded from normal queries (WHERE deleted_at IS NULL).
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            if not db_pedido:
                return False
            db_pedido.deleted_at = get_utc_now()
            uow.pedidos.update(db_pedido)
            return True
