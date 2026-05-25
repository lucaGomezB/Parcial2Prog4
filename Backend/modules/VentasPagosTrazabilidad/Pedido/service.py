from sqlmodel import Session
from typing import List, Optional
from .models import Pedido
from .schemas import PedidoCreate, PedidoUpdate
from ..uow import VentasPagosTrazabilidadUnitOfWork
from models.base import get_utc_now


class PedidoService:
    @staticmethod
    def get_all(session: Session, skip: int = 0, limit: int = 100) -> List[Pedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.pedidos.get_all(skip=skip, limit=limit)

    @staticmethod
    def get_by_id(session: Session, pedido_id: int) -> Optional[Pedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.pedidos.get_by_id(pedido_id)

    @staticmethod
    def get_by_usuario_id(session: Session, usuario_id: int, skip: int = 0, limit: int = 100) -> List[Pedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.pedidos.get_by_usuario_id(usuario_id, skip=skip, limit=limit)

    @staticmethod
    def create(session: Session, data: PedidoCreate) -> Pedido:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            costo_envio = data.costo_envio if data.direccion_id else 0.00
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
