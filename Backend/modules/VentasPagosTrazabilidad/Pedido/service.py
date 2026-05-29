from sqlmodel import Session, select, col
from sqlalchemy.orm import selectinload
from typing import List, Optional
from decimal import Decimal
from fastapi import HTTPException, status
from .models import Pedido
from .schemas import PedidoCreate, PedidoUpdate
from ..uow import VentasPagosTrazabilidadUnitOfWork
from ..DetallePedido.models import DetallePedido
from ..HistorialEstadoPedido.models import HistorialEstadoPedido
from models.base import get_utc_now
from modules.CatalogoDeProductos.Producto.models import ProductoMedida

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
            uow.pedidos.add(db_pedido)
            uow.pedidos.flush()  # para obtener ID antes de crear detalles

            # Crear DetallePedido snapshots si vienen en el create
            if data.detalles:
                for det in data.detalles:
                    # Validar medida si se especificó
                    medida_nombre = None
                    if det.medida_id is not None:
                        stmt = select(ProductoMedida).where(
                            ProductoMedida.id == det.medida_id,
                            ProductoMedida.producto_id == det.producto_id,
                        )
                        medida_db = session.exec(stmt).first()
                        if not medida_db:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Medida ID {det.medida_id} no encontrada para producto {det.producto_id}",
                            )
                        medida_nombre = medida_db.nombre

                    line_total = det.precio_snapshot * det.cantidad
                    uow.session.add(DetallePedido(
                        pedido_id=db_pedido.id,
                        producto_id=det.producto_id,
                        cantidad=det.cantidad,
                        nombre_snapshot=det.nombre_snapshot,
                        precio_snapshot=det.precio_snapshot,
                        subtotal_snap=line_total,
                        personalizacion=det.personalizacion,
                        medida_snapshot=medida_nombre,
                    ))

            uow.commit()
            uow.pedidos.refresh(db_pedido)
            return db_pedido

    @staticmethod
    def avanzar_estado(session: Session, pedido_id: int, usuario) -> Pedido:
        """Avanza el pedido al siguiente estado según la FSM.
        Registra el cambio en HistorialEstadoPedido (INSERT-only).
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

            if estado_actual not in TRANSICIONES_VALIDAS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No hay transición definida desde '{estado_actual}'",
                )

            estado_siguiente = TRANSICIONES_VALIDAS[estado_actual]

            # ── Validar stock antes de confirmar ──
            if estado_siguiente == "CONFIRMADO":
                from modules.CatalogoDeProductos.Producto.models import Producto

                errores_stock: list[dict] = []
                for det in db_pedido.detalles:
                    if det.medida_snapshot:
                        stmt_med = select(ProductoMedida).where(
                            ProductoMedida.producto_id == det.producto_id,
                            ProductoMedida.nombre == det.medida_snapshot,
                        )
                        medida = session.exec(stmt_med).first()
                        stock_disp = medida.stock if medida else 0
                        if stock_disp < det.cantidad:
                            errores_stock.append({
                                "producto_id": det.producto_id,
                                "nombre_producto": det.nombre_snapshot,
                                "medida": det.medida_snapshot,
                                "cantidad_solicitada": det.cantidad,
                                "stock_disponible": stock_disp,
                            })
                    else:
                        prod = session.get(Producto, det.producto_id)
                        stock_disp = prod.stock_cantidad if prod else 0
                        if stock_disp < det.cantidad:
                            errores_stock.append({
                                "producto_id": det.producto_id,
                                "nombre_producto": det.nombre_snapshot,
                                "medida": None,
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

                # ── Descontar stock al confirmar pedido ──
                for det in db_pedido.detalles:
                    if det.medida_snapshot:
                        stmt_med = select(ProductoMedida).where(
                            ProductoMedida.producto_id == det.producto_id,
                            ProductoMedida.nombre == det.medida_snapshot,
                        )
                        medida = session.exec(stmt_med).first()
                        if medida:
                            medida.stock = max(0, medida.stock - det.cantidad)
                            session.add(medida)
                    else:
                        prod = session.get(Producto, det.producto_id)
                        if prod:
                            prod.stock_cantidad = max(0, prod.stock_cantidad - det.cantidad)
                            session.add(prod)

            # Registrar en historial (INSERT-only)
            uow.session.add(HistorialEstadoPedido(
                pedido_id=db_pedido.id,
                estado_desde=estado_actual,
                estado_hacia=estado_siguiente,
                usuario_id=usuario.id if hasattr(usuario, 'id') else None,
            ))

            # Actualizar pedido
            db_pedido.estado_codigo = estado_siguiente
            uow.pedidos.add(db_pedido)
            uow.commit()
            uow.pedidos.refresh(db_pedido)
            return db_pedido

    @staticmethod
    def cancelar_pedido(session: Session, pedido_id: int, usuario) -> Pedido:
        """Cancela un pedido. ADMIN/PEDIDOS siempre pueden.
        Usuario común solo si el estado es anterior a EN_CAMINO.
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
                # Usuario común: solo puede cancelar si está antes de EN_CAMINO
                ordenes = {"PENDIENTE": 1, "CONFIRMADO": 2, "EN_PREP": 3, "EN_CAMINO": 4, "ENTREGADO": 5}
                if ordenes.get(estado_actual, 99) >= 4:  # EN_CAMINO o posterior
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="No puedes cancelar un pedido que ya está en camino o entregado",
                    )

            # Registrar en historial (INSERT-only)
            uow.session.add(HistorialEstadoPedido(
                pedido_id=db_pedido.id,
                estado_desde=estado_actual,
                estado_hacia="CANCELADO",
                usuario_id=usuario.id if hasattr(usuario, 'id') else None,
                motivo="Cancelado por usuario" if not es_admin else None,
            ))

            db_pedido.estado_codigo = "CANCELADO"
            uow.pedidos.add(db_pedido)
            uow.commit()
            uow.pedidos.refresh(db_pedido)
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
            uow.pedidos.add(db_pedido)
            uow.commit()
            uow.pedidos.refresh(db_pedido)
            return db_pedido

    @staticmethod
    def soft_delete(session: Session, pedido_id: int) -> bool:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_pedido = uow.pedidos.get_by_id(pedido_id)
            if not db_pedido:
                return False
            db_pedido.deleted_at = get_utc_now()
            uow.pedidos.add(db_pedido)
            uow.commit()
            return True
