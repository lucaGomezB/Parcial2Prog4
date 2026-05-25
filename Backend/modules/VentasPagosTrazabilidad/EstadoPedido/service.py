from sqlmodel import Session
from typing import List, Optional
from .models import EstadoPedido
from .schemas import EstadoPedidoCreate, EstadoPedidoUpdate
from ..uow import VentasPagosTrazabilidadUnitOfWork


class EstadoPedidoService:

    @staticmethod
    def get_all(session: Session) -> List[EstadoPedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.estados.get_all()

    @staticmethod
    def get_by_codigo(session: Session, codigo: str) -> Optional[EstadoPedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            return uow.estados.get_by_codigo(codigo)

    @staticmethod
    def create(session: Session, data: EstadoPedidoCreate) -> EstadoPedido:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_obj = EstadoPedido(**data.model_dump())
            uow.estados.add(db_obj)
            uow.commit()
            return db_obj

    @staticmethod
    def update(session: Session, codigo: str, data: EstadoPedidoUpdate) -> Optional[EstadoPedido]:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_obj = uow.estados.get_by_codigo(codigo)
            if not db_obj:
                return None
            values = data.model_dump(exclude_unset=True)
            for key, value in values.items():
                setattr(db_obj, key, value)
            uow.estados.add(db_obj)
            uow.commit()
            return db_obj

    @staticmethod
    def delete(session: Session, codigo: str) -> bool:
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            db_obj = uow.estados.get_by_codigo(codigo)
            if not db_obj:
                return False
            uow.session.delete(db_obj)
            uow.commit()
            return True
