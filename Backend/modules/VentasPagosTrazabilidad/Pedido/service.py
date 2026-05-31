from sqlmodel import Session, select, col
from sqlalchemy.orm import selectinload
from typing import List, Optional
from decimal import Decimal
from fastapi import HTTPException, status
import math
from .models import Pedido
from .schemas import PedidoCreate, PedidoUpdate, ValidarStockInput, ValidarStockResponse, ValidarStockDetalleResponse
from ..uow import VentasPagosTrazabilidadUnitOfWork
from ..DetallePedido.models import DetallePedido
from models.base import get_utc_now

ESTADOS_TERMINALES = {"ENTREGADO", "CANCELADO"}

TRANSICIONES_VALIDAS: dict[str, str] = {
    "PENDIENTE": "CONFIRMADO",
    "CONFIRMADO": "EN_PREP",
    "EN_PREP": "EN_CAMINO",
    "EN_CAMINO": "ENTREGADO",
}


class PedidoService:
    @staticmethod
    def _eager(stmt):
        """Agrega selectinload para detalles en cualquier query de Pedido."""
        return stmt.options(
            selectinload(Pedido.detalles),
            selectinload(Pedido.estado),
            selectinload(Pedido.usuario),
        )

    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100) -> List[Pedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            stmt = PedidoService._eager(select(Pedido).offset(skip).limit(limit))
            return uow.session.exec(stmt).all()

    @staticmethod
    def get_by_id(session: Session, pedido_id: int) -> Optional[Pedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            stmt = PedidoService._eager(select(Pedido).where(Pedido.id == pedido_id))
            return uow.session.exec(stmt).first()

    @staticmethod
    def get_by_usuario_id(session: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            stmt = PedidoService._eager(
                select(Pedido)
                .where(Pedido.usuario_id == usuario_id, col(Pedido.deleted_at).is_(None))
                .offset(skip).limit(limit)
                .order_by(Pedido.created_at.desc())
            )
            return uow.session.exec(stmt).all()

    @staticmethod
    def get_activos(session: Session, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Retorna pedidos que NO estén en estado terminal, ordenados por created_at DESC."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            stmt = PedidoService._eager(
                select(Pedido)
                .where(col(Pedido.estado_codigo).not_in(ESTADOS_TERMINALES))
                .where(col(Pedido.deleted_at).is_(None))
                .offset(skip).limit(limit)
                .order_by(Pedido.created_at.desc())
            )
            return uow.session.exec(stmt).all()

    @staticmethod
    def get_historial(session: Session, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Retorna pedidos en estado terminal (ENTREGADO, CANCELADO), ordenados por updated_at DESC."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            stmt = PedidoService._eager(
                select(Pedido)
                .where(col(Pedido.estado_codigo).in_(ESTADOS_TERMINALES))
                .where(col(Pedido.deleted_at).is_(None))
                .offset(skip).limit(limit)
                .order_by(Pedido.updated_at.desc())
            )
            return uow.session.exec(stmt).all()

    @staticmethod
    def get_historial_by_usuario(session: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        """Retorna pedidos en estado terminal de un usuario específico, ordenados por updated_at DESC."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            stmt = PedidoService._eager(
                select(Pedido)
                .where(Pedido.usuario_id == usuario_id)
                .where(col(Pedido.estado_codigo).in_(ESTADOS_TERMINALES))
                .where(col(Pedido.deleted_at).is_(None))
                .offset(skip).limit(limit)
                .order_by(Pedido.updated_at.desc())
            )
            return uow.session.exec(stmt).all()

    @staticmethod
    def create(session: Session, data: PedidoCreate) -> Pedido:
        # Auto-select principal address if not specified
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
            uow.flush()  # para obtener ID antes de crear detalles

            # Crear DetallePedido snapshots si vienen en el create
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

            # ── Registrar historial de creación (estado_desde=NULL) ──
            uow.avanzar_estado(
                pedido=db_pedido,
                estado_anterior=None,        # NULL = creación
                estado_siguiente="PENDIENTE",
                usuario_id=data.usuario_id,  # quien creó el pedido
            )

            uow.refresh(db_pedido)
            return db_pedido

    @staticmethod
    def validar_stock_items(session: Session, data: ValidarStockInput) -> ValidarStockResponse:
        """Verifica stock para un conjunto de items SIN crear pedido ni efectos secundarios."""
        from modules.CatalogoDeProductos.Producto.models import Producto

        errores: list[ValidarStockDetalleResponse] = []

        for det in data.detalles:
            # Validar contra Producto.stock_cantidad
            prod = session.get(Producto, det.producto_id)
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
        """Actualiza o elimina un detalle de pedido PENDIENTE. cantidad=0 lo elimina."""
        from ..DetallePedido.models import DetallePedido

        db_pedido = PedidoService.get_by_id(session, pedido_id)
        if not db_pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        if db_pedido.estado_codigo != "PENDIENTE":
            raise HTTPException(status_code=400, detail="Solo se pueden modificar detalles en pedidos PENDIENTE")

        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            stmt = select(DetallePedido).where(
                DetallePedido.pedido_id == pedido_id,
                DetallePedido.producto_id == producto_id,
            )
            detalle = session.exec(stmt).first()
            if not detalle:
                raise HTTPException(status_code=404, detail="Detalle no encontrado en el pedido")

            if cantidad <= 0:
                uow.delete(detalle)
            else:
                detalle.cantidad = cantidad
                detalle.subtotal_snap = detalle.precio_snapshot * cantidad
                uow.add(detalle)

            # Recalcular total del pedido
            detalles_restantes = session.exec(
                select(DetallePedido).where(DetallePedido.pedido_id == pedido_id)
            ).all()
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
        """Avanza el pedido al siguiente estado según la FSM.
        Registra el cambio en HistorialEstadoPedido (INSERT-only).
        Retorna (pedido, estado_anterior).
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

            # ── Validar stock antes de confirmar ──
            if estado_siguiente == "CONFIRMADO":
                from modules.CatalogoDeProductos.Producto.models import Producto

                errores_stock: list[dict] = []
                for det in db_pedido.detalles:
                    prod = session.get(Producto, det.producto_id)
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

                # ── Validar stock de ingredientes ──
                from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
                from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente

                errores_ing_stock: list[dict] = []
                for det in db_pedido.detalles:
                    stmt_pi = select(ProductoIngrediente).where(
                        ProductoIngrediente.producto_id == det.producto_id
                    )
                    for pi in session.exec(stmt_pi):
                        cantidad_needed = pi.cantidad * det.cantidad
                        ing = session.get(Ingrediente, pi.ingrediente_id)
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

                # ── Descontar stock al confirmar pedido ──
                for det in db_pedido.detalles:
                    prod = session.get(Producto, det.producto_id)
                    if prod:
                        prod.stock_cantidad = max(0, prod.stock_cantidad - det.cantidad)
                        session.add(prod)

                # ── Descontar stock de ingredientes ──
                from modules.CatalogoDeProductos.producto_ingrediente import ProductoIngrediente
                from modules.CatalogoDeProductos.Ingrediente.models import Ingrediente

                for det in db_pedido.detalles:
                    stmt_pi = select(ProductoIngrediente).where(
                        ProductoIngrediente.producto_id == det.producto_id
                    )
                    for pi in session.exec(stmt_pi):
                        cantidad_a_descontar = int(math.ceil(pi.cantidad * det.cantidad))
                        ing = session.get(Ingrediente, pi.ingrediente_id)
                        if ing:
                            ing.stock_actual = max(0, ing.stock_actual - cantidad_a_descontar)
                            session.add(ing)

            # ── Transición atómica via UoW ──
            usuario_id = usuario.id if hasattr(usuario, 'id') else None
            uow.avanzar_estado(
                pedido=db_pedido,
                estado_anterior=estado_anterior,
                estado_siguiente=estado_siguiente,
                usuario_id=usuario_id,
            )

            # NOTA: NO hacer uow.refresh(db_pedido) aquí — el refresh
            # antes del commit revierte el cambio de estado en memoria
            # (el objeto ya tiene estado_codigo correcto).
            return (db_pedido, estado_anterior)

    @staticmethod
    def cancelar_pedido(session: Session, pedido_id: int, usuario) -> Pedido:
        """Cancela un pedido. ADMIN/PEDIDOS siempre pueden.
        Usuario común solo en PENDIENTE o CONFIRMADO.
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

            # Verificar permisos
            user_roles = [r.codigo for r in usuario.roles] if hasattr(usuario, 'roles') else []
            es_admin = "ADMIN" in user_roles or "PEDIDOS" in user_roles

            if not es_admin:
                # Usuario común: solo puede cancelar si está en PENDIENTE o CONFIRMADO
                estados_permitidos_cliente = {"PENDIENTE", "CONFIRMADO"}
                if estado_actual not in estados_permitidos_cliente:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No puedes cancelar un pedido que ya está en preparación o en camino",
                    )

            usuario_id = usuario.id if hasattr(usuario, 'id') else None
            uow.avanzar_estado(
                pedido=db_pedido,
                estado_anterior=estado_actual,
                estado_siguiente="CANCELADO",
                usuario_id=usuario_id,
                motivo="Cancelado por usuario" if not es_admin else None,
            )

            # SIN refresh — mismo motivo que en avanzar_estado
            return db_pedido

    @staticmethod
    def update(session: Session, pedido_id: int, data: PedidoUpdate) -> Optional[Pedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            if not db_pedido:
                return None
            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(db_pedido, key, value)
            uow.add(db_pedido)
            uow.refresh(db_pedido)
            return db_pedido

    @staticmethod
    def soft_delete(session: Session, pedido_id: int) -> bool:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            if not db_pedido:
                return False
            db_pedido.deleted_at = get_utc_now()
            uow.add(db_pedido)
            return True
