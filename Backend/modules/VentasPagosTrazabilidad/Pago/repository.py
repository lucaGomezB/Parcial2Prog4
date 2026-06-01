"""
Pago repository — data access layer for payments.

Provides queries for looking up payments by:
    - pedido_id: all payments for a given order (newest first)
    - mp_payment_id: lookup by MercadoPago's payment ID (for webhook matching)
    - external_reference: lookup by our custom reference (for idempotency)
    - idempotency_key: deduplication check for webhook events
"""
from sqlmodel import Session, select
from typing import List, Optional
from models.base_repository import BaseRepository
from .models import Pago


class PagoRepository(BaseRepository[Pago]):
    """Repository for Pago with MercadoPago-specific lookups."""

    def __init__(self, session: Session):
        super().__init__(session, Pago)

    def get_by_pedido(self, pedido_id: int) -> List[Pago]:
        """Return all payments for an order, newest first."""
        statement = select(Pago).where(Pago.pedido_id == pedido_id).order_by(Pago.created_at.desc())
        return self.session.exec(statement).all()

    def get_by_mp_payment_id(self, mp_payment_id: int) -> Optional[Pago]:
        """Lookup a payment by MercadoPago's payment ID (for webhook matching)."""
        statement = select(Pago).where(Pago.mp_payment_id == mp_payment_id)
        return self.session.exec(statement).first()

    def get_by_external_reference(self, external_reference: str) -> Optional[Pago]:
        """Lookup a payment by our external reference string."""
        statement = select(Pago).where(Pago.external_reference == external_reference)
        return self.session.exec(statement).first()

    def get_by_idempotency_key(self, idempotency_key: str) -> Optional[Pago]:
        """Lookup a payment by idempotency key (prevents double-processing of webhooks)."""
        statement = select(Pago).where(Pago.idempotency_key == idempotency_key)
        return self.session.exec(statement).first()
