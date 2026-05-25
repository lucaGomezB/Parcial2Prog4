from sqlmodel import Session
from typing import List
from .models import DetallePedido
from .schemas import DetallePedidoCreate
from ..uow import VentasPagosTrazabilidadUnitOfWork


class DetallePedidoService:
    @staticmethod
    def get_by_pedido(session: Session, pedido_id: int) -> List[DetallePedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.detalles.get_by_pedido(pedido_id)

    @staticmethod
    def create(session: Session, pedido_id: int, data: DetallePedidoCreate) -> DetallePedido:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            subtotal = data.precio_snapshot * data.cantidad
            db_detalle = DetallePedido(
                pedido_id=pedido_id,
                producto_id=data.producto_id,
                cantidad=data.cantidad,
                nombre_snapshot=data.nombre_snapshot,
                precio_snapshot=data.precio_snapshot,
                subtotal_snap=subtotal,
                personalizacion=data.personalizacion,
            )
            uow.detalles.add(db_detalle)
            uow.commit()
            return db_detalle
