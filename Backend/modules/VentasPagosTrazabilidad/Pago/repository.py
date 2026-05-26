from sqlmodel import Session, select
from typing import List, Optional
from models.base_repository import BaseRepository
from .models import Pago


class PagoRepository(BaseRepository[Pago]):
    def __init__(self, session: Session):
        super().__init__(session, Pago)

    def get_by_pedido(self, pedido_id: int) -> List[Pago]:
        statement = select(Pago).where(Pago.pedido_id == pedido_id).order_by(Pago.created_at.desc())
        return self.session.exec(statement).all()

    def get_by_mp_payment_id(self, mp_payment_id: int) -> Optional[Pago]:
        statement = select(Pago).where(Pago.mp_payment_id == mp_payment_id)
        return self.session.exec(statement).first()

    def get_by_external_reference(self, external_reference: str) -> Optional[Pago]:
        statement = select(Pago).where(Pago.external_reference == external_reference)
        return self.session.exec(statement).first()

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Pago]:
        statement = select(Pago).where(Pago.idempotency_key == idempotency_key)
        return self.session.exec(statement).first()
