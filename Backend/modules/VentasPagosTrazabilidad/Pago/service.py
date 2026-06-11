"""
Pago service — MercadoPago payment business logic.

This service provides:
    - init_mp_payment: Creates a Pago record with pending status and UUIDs.
      Does NOT call the MP API yet (placeholder for future integration).
    - update_pago_status: Updates an existing Pago record from webhook data.
    - get_pagos_by_pedido: Lists all payments for an order (read-only).

PATTERN: Write operations use VentasPagosTrazabilidadUnitOfWork for atomicity.
Read operations use the repository directly (no UoW) to avoid commit/expire.

NESTED UoW SUPPORT:
    init_mp_payment accepts an optional UoW parameter. When provided (e.g.,
    when called from PedidoService.avanzar_estado which already has an active
    UoW), the payment is created within the caller's transaction boundary.
    When omitted, a new UoW is created (standalone call from router).
"""
from sqlmodel import Session
from typing import List, Optional
from decimal import Decimal
import uuid

from .models import Pago
from .repository import PagoRepository
from .schemas import PagoRead
from ..uow import VentasPagosTrazabilidadUnitOfWork
from ..Pedido.service import PedidoService


class PagoService:
    """Business logic for MercadoPago payment operations."""

    @staticmethod
    def init_mp_payment(
        session: Session,
        pedido_id: int,
        uow: Optional[VentasPagosTrazabilidadUnitOfWork] = None,
    ) -> PagoRead:
        """Create a pending Pago record for an order.

        This does NOT call the MercadoPago API. It only creates the
        database record with a pending status. The actual MP API call
        will be added in a future integration.

        When called from within an existing UoW (e.g., from
        PedidoService.avanzar_estado), pass the active UoW to keep
        everything in the same transaction boundary.

        Steps:
            1. Fetch the Pedido to validate existence and get the total
            2. Generate external_reference and idempotency_key as UUIDs
            3. Create the Pago record inside a UoW transaction
            4. Return the PagoRead schema

        Args:
            session: SQLModel database session.
            pedido_id: ID of the order to associate the payment with.
            uow: Optional active UoW. If provided, the payment is added
                 to this UoW instead of creating a new one.

        Returns:
            PagoRead with the created payment record.

        Raises:
            ValueError: If pedido_id does not exist.
        """
        # Validate the pedido exists and get its total
        pedido = PedidoService.get_by_id(session, pedido_id)
        if not pedido:
            raise ValueError(f"Pedido {pedido_id} no encontrado")

        # If a Pago already exists for this pedido, return it (idempotent).
        # This handles the case where the CONFIRMADO hook already created one
        # and the frontend also calls initPayment separately.
        repo = PagoRepository(session)
        existing = repo.get_by_pedido(pedido_id)
        if existing:
            return PagoRead.model_validate(existing[0])

        external_reference = str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())

        pago = Pago(
            pedido_id=pedido_id,
            mp_status="pending",
            mp_status_detail=None,
            mp_payment_id=None,
            external_reference=external_reference,
            idempotency_key=idempotency_key,
            transaction_amount=pedido.total,
            payment_method_id=None,
        )

        if uow is not None:
            # Called from within an existing UoW — use the caller's transaction
            uow.add(pago)
            uow.refresh(pago)
            return PagoRead.model_validate(pago)

        # Standalone call — create a new UoW
        with VentasPagosTrazabilidadUnitOfWork(session) as new_uow:
            new_uow.add(pago)
            new_uow.refresh(pago)
            return PagoRead.model_validate(pago)

    @staticmethod
    def update_pago_status(
        session: Session,
        mp_payment_id: int,
        mp_status: str,
        mp_status_detail: str | None = None,
    ) -> PagoRead:
        """Update a Pago record's status from a MercadoPago webhook callback.

        Looks up the payment by mp_payment_id and applies the new status
        and status_detail fields inside a UoW transaction.

        Args:
            session: SQLModel database session.
            mp_payment_id: MercadoPago's internal payment ID.
            mp_status: New status value (approved, rejected, etc.).
            mp_status_detail: Optional detailed status description.

        Returns:
            PagoRead with the updated payment record.

        Raises:
            ValueError: If no Pago exists with the given mp_payment_id.
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            pago = uow.pagos.get_by_mp_payment_id(mp_payment_id)
            if not pago:
                raise ValueError(f"Pago con MP ID {mp_payment_id} no encontrado")

            pago.mp_status = mp_status
            pago.mp_status_detail = mp_status_detail
            pago.mp_payment_id = mp_payment_id
            uow.add(pago)
            return PagoRead.model_validate(pago)

    @staticmethod
    def get_pagos_by_pedido(session: Session, pedido_id: int) -> List[PagoRead]:
        """List all payments for an order, newest first.

        Read-only operation: uses repository directly without UoW.

        Args:
            session: SQLModel database session.
            pedido_id: Order ID to fetch payments for.

        Returns:
            List of PagoRead, newest first. Empty list if no payments exist.
        """
        repo = PagoRepository(session)
        pagos = repo.get_by_pedido(pedido_id)
        return [PagoRead.model_validate(p) for p in pagos]
