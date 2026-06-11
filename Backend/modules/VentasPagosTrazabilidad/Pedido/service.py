"""
Pedido service — the core business logic module for orders.

This is the most important file in the Sales module. It contains:
    - Order creation with detail snapshots
    - Finite State Machine (FSM) for state transitions
    - Stock deduction for products AND ingredients at confirmation time
    - Total calculation (subtotal, descuento, costo_envio, total)
    - Pre-creation stock validation
    - Cancelation with role-based permissions
    - Append-only state change history

PATTERN: Unit of Work (UoW)
    All write operations go through VentasPagosTrazabilidadUnitOfWork,
    which ensures atomicity: everything commits or everything rolls back.
Read-only operations use the repository directly without UoW to avoid
the commit/expire problem.
"""
from sqlmodel import Session
from typing import List, Optional
from decimal import Decimal
from fastapi import HTTPException, status
import math
from .models import Pedido
from .repository import PedidoRepository
from .schemas import PedidoCreate, PedidoUpdate, ValidarStockInput, ValidarStockResponse, ValidarStockDetalleResponse
from ..uow import VentasPagosTrazabilidadUnitOfWork
from ..DetallePedido.models import DetallePedido
from ..HistorialEstadoPedido.models import HistorialEstadoPedido
from models.base import get_utc_now


# ---------------------------------------------------------------------------
# FINITE STATE MACHINE (FSM) definition
# ---------------------------------------------------------------------------
# Full flow:
#
#   PENDIENTE --[confirm]--> CONFIRMADO --[start prep]--> EN_PREP
#       |                                                        |
#       |  (customer or admin)         [out for delivery]        |
#       +--[cancel]--> CANCELADO       EN_CAMINO --[deliver]--> ENTREGADO
#
# Terminal states (no further transitions allowed):
#   - ENTREGADO: delivery completed
#   - CANCELADO: order cancelled
#
# State transition rules:
#   - Only one state advance at a time
#   - From PENDIENTE or CONFIRMADO: customer or admin can CANCEL
#   - From EN_PREP or EN_CAMINO: only ADMIN/PEDIDOS can cancel
#   - ENTREGADO and CANCELADO are TERMINAL — no coming back
# ---------------------------------------------------------------------------
ESTADOS_TERMINALES = {"ENTREGADO", "CANCELADO"}

TRANSICIONES_VALIDAS: dict[str, str] = {
    "PENDIENTE": "CONFIRMADO",
    "CONFIRMADO": "EN_PREP",
    "EN_PREP": "EN_CAMINO",
    "EN_CAMINO": "ENTREGADO",
}


class PedidoService:
    """Business logic for the Order entity — FSM, stock validation, and CRUD."""

    @staticmethod
    def _registrar_transicion(uow, pedido, estado_anterior, estado_siguiente, usuario_id=None, motivo=None):
        """Register an atomic state transition: INSERT audit trail + UPDATE order state.

        This is the ONLY place where HistorialEstadoPedido rows are created and
        where pedido.estado_codigo is modified. Both operations happen within
        the same UoW transaction to ensure atomicity.

        Args:
            uow: Active VentasPagosTrazabilidadUnitOfWork instance.
            pedido: The Pedido ORM instance to transition.
            estado_anterior: Previous state (None = creation event).
            estado_siguiente: Target state string (e.g. 'CONFIRMADO', 'CANCELADO').
            usuario_id: Who triggered the transition (None = system/webhook).
            motivo: Optional reason string (e.g. "Cancelado por usuario").
        """
        # Insert audit trail row (append-only — never modified after creation)
        uow.add(HistorialEstadoPedido(
            pedido_id=pedido.id,
            estado_desde=estado_anterior,
            estado_hacia=estado_siguiente,
            usuario_id=usuario_id,
            motivo=motivo,
        ))
        # Update the order's current state
        pedido.estado_codigo = estado_siguiente
        uow.pedidos.add(pedido)

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """List ALL orders with pagination. Intended for ADMIN/PEDIDOS users.

        Read-only: uses repository directly (no UoW) to avoid commit/expire.
        """
        repo = PedidoRepository(session)
        return repo.get_all_eager(skip=skip, limit=limit)

    @staticmethod
    def get_by_id(session: Session, pedido_id: int) -> Optional[Pedido]:
        """Fetch a single order by its primary key with eager-loaded details.

        Read-only: uses repository directly (no UoW).
        """
        repo = PedidoRepository(session)
        return repo.get_by_id_eager(pedido_id)

    @staticmethod
    def get_by_usuario_id(session: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Fetch non-deleted orders for a specific user, newest first.

        Read-only: uses repository directly (no UoW).
        """
        repo = PedidoRepository(session)
        return repo.get_by_usuario_id_eager(usuario_id, skip=skip, limit=limit)

    @staticmethod
    def get_activos(session: Session, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Fetch non-terminal orders (not ENTREGADO or CANCELADO), newest first.

        Used for the "active orders" dashboard.
        Read-only: uses repository directly (no UoW).
        """
        repo = PedidoRepository(session)
        return repo.get_activos(skip=skip, limit=limit)

    @staticmethod
    def get_historial(session: Session, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Fetch terminal-state orders (ENTREGADO or CANCELADO), most recently updated first.

        Used for the order history view.
        Read-only: uses repository directly (no UoW).
        """
        repo = PedidoRepository(session)
        return repo.get_historial(skip=skip, limit=limit)

    @staticmethod
    def get_historial_by_usuario(session: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Fetch terminal-state orders for a specific user, most recently updated first.

        Read-only: uses repository directly (no UoW).
        """
        repo = PedidoRepository(session)
        return repo.get_historial_by_usuario(usuario_id, skip=skip, limit=limit)

    @staticmethod
    def create(session: Session, data: PedidoCreate) -> Pedido:
        """Create a new order (the MAIN order creation function).

        Step-by-step logic:
        1. Auto-select the user's primary delivery address if none specified
        2. Calculate totals: costo_envio=0 if pickup, total = subtotal - descuento + costo_envio
        3. Create the Pedido row with estado_codigo = "PENDIENTE"
        4. Create DetallePedido rows with price/name snapshots
        5. Register the creation event in HistorialEstadoPedido (estado_desde=NULL)

        IMPORTANT: Stock is NOT deducted here. It is deducted at CONFIRMADO
        transition time (avanzar_estado). The order sits in PENDIENTE until
        it is actively confirmed.
        """
        # Auto-select user's primary address if none provided
        if data.direccion_id is None:
            from modules.IdentidadYAcceso.DireccionEntrega.repository import DireccionEntregaRepository

            direccion_repo = DireccionEntregaRepository(session)
            principal = direccion_repo.get_principal(data.usuario_id)
            if principal:
                data.direccion_id = principal.id

        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            costo_envio = data.costo_envio if data.direccion_id else Decimal('0.00')
            total = data.subtotal - data.descuento + costo_envio
            if total < 0:
                raise ValueError("El total no puede ser negativo")

            db_pedido = Pedido(
                usuario_id=data.usuario_id,
                direccion_id=data.direccion_id,
                estado_codigo="PENDIENTE",
                forma_pago_codigo=data.forma_pago_codigo,
                subtotal=data.subtotal,
                descuento=data.descuento,
                costo_envio=costo_envio,
                total=total,
                notas=data.notas,
            )
            uow.add(db_pedido)
            uow.flush()  # Flush to obtain the pedido ID before creating details

            # Create DetallePedido snapshots if provided in the create request
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

            # Register the creation in history (estado_desde=NULL = creation)
            PedidoService._registrar_transicion(
                uow,
                pedido=db_pedido,
                estado_anterior=None,        # NULL = creation event
                estado_siguiente="PENDIENTE",
                usuario_id=data.usuario_id,  # Who created the order
            )

            uow.refresh(db_pedido)
            return db_pedido

    @staticmethod
    def validar_stock_items(session: Session, data: ValidarStockInput) -> ValidarStockResponse:
        """Validate stock availability WITHOUT creating an order or any side effects.

        This is a READ-ONLY check used by the frontend cart to show stock
        errors in real-time. The REAL stock validation (with deduction)
        happens in avanzar_estado when the order transitions to CONFIRMADO.
        """
        repo = PedidoRepository(session)
        errores: list[ValidarStockDetalleResponse] = []

        for det in data.detalles:
            prod = repo.get_producto(det.producto_id)
            if not prod:
                raise HTTPException(status_code=404, detail=f"Producto {det.producto_id} no encontrado")
            stock_disp = prod.stock_cantidad
            if stock_disp < det.cantidad:
                errores.append(ValidarStockDetalleResponse(
                    producto_id=det.producto_id,
                    nombre_producto=prod.nombre,
                    cantidad_solicitada=det.cantidad,
                    stock_disponible=stock_disp,
                ))

        return ValidarStockResponse(
            valido=len(errores) == 0,
            detalles=errores,
        )

    @staticmethod
    def actualizar_detalle(session: Session, pedido_id: int, producto_id: int, cantidad: int) -> Pedido:
        """Update or remove a detail line on a PENDIENTE order.

        cantidad=0 removes the detail line.
        Only works on PENDIENTE orders — once CONFIRMADO, details are frozen
        because stock has already been deducted.

        After modification, subtotal and total are recalculated from the
        remaining details' subtotal_snap values.
        """
        repo = PedidoRepository(session)

        db_pedido = repo.get_by_id_eager(pedido_id)
        if not db_pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        if db_pedido.estado_codigo != "PENDIENTE":
            raise HTTPException(status_code=400, detail="Solo se pueden modificar detalles en pedidos PENDIENTE")

        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            detalle = repo.get_detalle_by_producto(pedido_id, producto_id)
            if not detalle:
                raise HTTPException(status_code=404, detail="Detalle no encontrado en el pedido")

            if cantidad <= 0:
                uow.delete(detalle)
            else:
                detalle.cantidad = cantidad
                detalle.subtotal_snap = detalle.precio_snapshot * cantidad
                uow.add(detalle)

            # Recalculate order totals from remaining details
            detalles_restantes = repo.get_detalles(pedido_id)
            nuevo_subtotal = sum(d.subtotal_snap for d in detalles_restantes)
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            db_pedido.subtotal = nuevo_subtotal
            db_pedido.total = nuevo_subtotal - db_pedido.descuento + (db_pedido.costo_envio or Decimal('0.00'))
            if db_pedido.total < 0:
                db_pedido.total = Decimal('0.00')
            uow.add(db_pedido)
            uow.refresh(db_pedido)
            return db_pedido

    @staticmethod
    def avanzar_estado(session: Session, pedido_id: int, usuario) -> tuple[Pedido, str]:
        """Advance the order to the next FSM state.

        This is the CORE state transition method. Flow:
        1. Fetch the order, validate it exists
        2. Check it's not in a terminal state
        3. Look up the next state from TRANSICIONES_VALIDAS
        4. If transitioning to CONFIRMADO:
            a. Validate product stock sufficiency
            b. Validate ingredient stock sufficiency
            c. Deduct product stock (stock_cantidad -= cantidad)
            d. Deduct ingredient stock (stock_actual -= pi.cantidad * det.cantidad)
        5. Register the change in HistorialEstadoPedido (append-only)
        6. Return (pedido, estado_anterior)

        IMPORTANT: Do NOT call refresh() before commit() — it would overwrite
        the in-memory estado_codigo with the pre-transaction value.
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            if not db_pedido:
                raise HTTPException(status_code=404, detail="Pedido no encontrado")

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

            # Stock validation and deduction only occurs at CONFIRMADO
            if estado_siguiente == "CONFIRMADO":
                errores_stock: list[dict] = []
                for det in db_pedido.detalles:
                    prod = uow.pedidos.get_producto(det.producto_id)
                    stock_disp = prod.stock_cantidad if prod else 0
                    if stock_disp < det.cantidad:
                        errores_stock.append({
                            "producto_id": det.producto_id,
                            "nombre_producto": det.nombre_snapshot,
                            "cantidad_solicitada": det.cantidad,
                            "stock_disponible": stock_disp,
                        })

                if errores_stock:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "stock_insuficiente",
                            "mensaje": "Stock insuficiente para confirmar el pedido. Revisá los detalles.",
                            "detalles": errores_stock,
                        },
                    )

                # Validate ingredient stock levels
                errores_ing_stock: list[dict] = []
                for det in db_pedido.detalles:
                    for pi in uow.pedidos.get_producto_ingredientes(det.producto_id):
                        cantidad_needed = pi.cantidad * det.cantidad
                        ing = uow.pedidos.get_ingrediente(pi.ingrediente_id)
                        if ing and ing.stock_actual < cantidad_needed:
                            errores_ing_stock.append({
                                "ingrediente": ing.nombre,
                                "disponible": ing.stock_actual,
                                "requerido": int(math.ceil(cantidad_needed)),
                            })

                if errores_ing_stock:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "error": "stock_insuficiente",
                            "ingredientes": errores_ing_stock,
                        },
                    )

                # Deduct product stock at confirmation
                for det in db_pedido.detalles:
                    prod = uow.pedidos.get_producto(det.producto_id)
                    if prod:
                        prod.stock_cantidad = max(0, prod.stock_cantidad - det.cantidad)
                        uow.add(prod)

                # Deduct ingredient stock at confirmation
                for det in db_pedido.detalles:
                    for pi in uow.pedidos.get_producto_ingredientes(det.producto_id):
                        cantidad_a_descontar = int(math.ceil(pi.cantidad * det.cantidad))
                        ing = uow.pedidos.get_ingrediente(pi.ingrediente_id)
                        if ing:
                            ing.stock_actual = max(0, ing.stock_actual - cantidad_a_descontar)
                            uow.add(ing)

                # Create MercadoPago payment record if this is an MP order
                if db_pedido.forma_pago_codigo == "MERCADOPAGO":
                    # Lazy import to avoid circular dependency:
                    # PagoService -> PedidoService -> PagoService
                    from ..Pago.service import PagoService as _PagoService

                    _PagoService.init_mp_payment(session, pedido_id, uow=uow)

            # Atomic transition: audit trail + state update
            usuario_id = usuario.id if hasattr(usuario, 'id') else None
            PedidoService._registrar_transicion(
                uow,
                pedido=db_pedido,
                estado_anterior=estado_anterior,
                estado_siguiente=estado_siguiente,
                usuario_id=usuario_id,
            )

            # NOTE: Do NOT call uow.refresh(db_pedido) here — refresh before
            # commit reverts the in-memory estado_codigo to its pre-transaction
            # value, which would undo the transition we just applied.
            return (db_pedido, estado_anterior)

    @staticmethod
    def cancelar_pedido(session: Session, pedido_id: int, usuario) -> Pedido:
        """Cancel an order. ADMIN/PEDIDOS users can cancel anytime.

        Permission rules:
            - ADMIN or PEDIDOS roles: can cancel ALWAYS
            - Regular customer: only if order is in PENDIENTE or CONFIRMADO
              (once EN_PREP, the kitchen has started — customer cannot cancel)
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            if not db_pedido:
                raise HTTPException(status_code=404, detail="Pedido no encontrado")

            estado_actual = db_pedido.estado_codigo
            if estado_actual in ESTADOS_TERMINALES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El pedido ya está en estado terminal '{estado_actual}'",
                )

            # Check permissions
            user_roles = [r.codigo for r in usuario.roles] if hasattr(usuario, 'roles') else []
            es_admin = "ADMIN" in user_roles or "PEDIDOS" in user_roles

            if not es_admin:
                # Regular user: only PENDIENTE or CONFIRMADO can be cancelled
                estados_permitidos_cliente = {"PENDIENTE", "CONFIRMADO"}
                if estado_actual not in estados_permitidos_cliente:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No puedes cancelar un pedido que ya está en preparación o en camino",
                    )

            usuario_id = usuario.id if hasattr(usuario, 'id') else None
            PedidoService._registrar_transicion(
                uow,
                pedido=db_pedido,
                estado_anterior=estado_actual,
                estado_siguiente="CANCELADO",
                usuario_id=usuario_id,
                motivo="Cancelado por usuario" if not es_admin else None,
            )

            # No refresh — same reason as in avanzar_estado
            return db_pedido

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

            uow.add(db_pedido)
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
            uow.add(db_pedido)
            return True
