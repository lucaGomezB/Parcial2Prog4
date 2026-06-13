"""
Pago service — MercadoPago payment business logic.

This service provides:
    - init_mp_payment: Creates a preference in MercadoPago, returns the
      checkout init_point URL for redirect-based payment.
    - update_pago_status: Updates an existing Pago record from webhook data.
    - get_pagos_by_pedido: Lists all payments for an order (read-only).
    - get_payment_from_mp: Fetches payment details from MP API by MP payment ID.

PATTERN: Write operations use VentasPagosTrazabilidadUnitOfWork for atomicity.
Read operations use the repository directly (no UoW) to avoid commit/expire.
"""
import os
import uuid
import logging
from sqlmodel import Session
from typing import List, Optional
from decimal import Decimal

import mercadopago
from .models import Pago
from .repository import PagoRepository
from .schemas import PagoRead
from ..uow import VentasPagosTrazabilidadUnitOfWork
from ..Pedido.service import PedidoService

logger = logging.getLogger(__name__)

# ── MercadoPago SDK singleton (lazy init) ──
_sdk: mercadopago.SDK | None = None


def _get_mp_sdk() -> mercadopago.SDK:
    """Return a singleton MercadoPago SDK instance.

    Reads MP_ACCESS_TOKEN from environment on first call.
    Raises RuntimeError if the token is missing or still a placeholder.
    """
    global _sdk
    if _sdk is None:
        token = os.getenv("MP_ACCESS_TOKEN", "")
        if not token or "000000" in token:
            raise RuntimeError(
                "MP_ACCESS_TOKEN no configurado o es un placeholder. "
                "Configuralo en Backend/.env con un token real de MercadoPago."
            )
        _sdk = mercadopago.SDK(token)
    return _sdk


# ── Ngrok / webhook base URL ──
def _get_webhook_base_url() -> str:
    """Return the base URL for webhook notifications.

    Uses NGROK_URL from env if set, falls back to localhost:8000.
    The user should set NGROK_URL to their ngrok tunnel URL for
    MercadoPago IPN to reach the webhook endpoint.
    """
    return os.getenv("NGROK_URL", "http://localhost:8000").rstrip("/")


# ── Frontend base URL for redirect back_urls ──
def _get_frontend_url() -> str:
    """Return the frontend base URL for MercadoPago back_urls redirects."""
    return os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


class PagoService:
    """Business logic for MercadoPago payment operations."""

    @staticmethod
    def init_mp_payment(
        session: Session,
        pedido_id: int,
        uow: Optional[VentasPagosTrazabilidadUnitOfWork] = None,
    ) -> tuple[PagoRead, str]:
        """Create a MercadoPago checkout preference and return the init_point.

        Steps:
            1. Fetch the Pedido to validate existence and get the total
            2. Check if a Pago already exists for this pedido (idempotent)
            3. Generate external_reference and idempotency_key as UUIDs
            4. Create the Pago record in DB
            5. Create a preference in MercadoPago via SDK
            6. Return (PagoRead, init_point) tuple

        Args:
            session: SQLModel database session.
            pedido_id: ID of the order to associate the payment with.
            uow: Optional active UoW. If provided, the payment is added
                 to this UoW instead of creating a new one.

        Returns:
            Tuple of (PagoRead, init_point_url). init_point is "#" if
            the MP SDK call fails (payment record still exists in DB).

        Raises:
            ValueError: If pedido_id does not exist.
            RuntimeError: If MP_ACCESS_TOKEN is not configured.
        """
        # Validate the pedido exists and get its total
        pedido = PedidoService.get_by_id(session, pedido_id)
        if not pedido:
            raise ValueError(f"Pedido {pedido_id} no encontrado")

        # ── Create the Pago record in DB ──
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
            uow.add(pago)
            uow.refresh(pago)
        else:
            with VentasPagosTrazabilidadUnitOfWork(session) as new_uow:
                new_uow.add(pago)
                new_uow.refresh(pago)

        # ── Create the preference in MercadoPago ──
        try:
            sdk = _get_mp_sdk()
            webhook_base = _get_webhook_base_url()
            frontend_url = _get_frontend_url()

            preference_data = {
                "items": [
                    {
                        "title": f"Pedido #{pedido_id}",
                        "quantity": 1,
                        "unit_price": float(pedido.total),
                        "currency_id": "ARS",
                    }
                ],
                "external_reference": external_reference,
                "back_urls": {
                    "success": f"{frontend_url}/pedidos/{pedido_id}",
                    "failure": f"{frontend_url}/carrito",
                    "pending": f"{frontend_url}/pedidos/{pedido_id}",
                },
                "auto_return": "approved",
                "notification_url": f"{webhook_base}/pagos/webhook",
                "purpose": "checkout",
            }

            preference_response = sdk.preference().create(preference_data)
            response_data = preference_response.get("response", {})

            if preference_response.get("status") not in (200, 201):
                logger.error(
                    "MP preference creation failed: %s",
                    preference_response.get("response", {}).get("message", "unknown error"),
                )
                # Pago record already exists in DB — return it without init_point
                return PagoRead.model_validate(pago), "#"

            init_point = response_data.get("init_point", "#")
            preference_id = response_data.get("id")

            # Update the Pago record with the MP preference ID
            if uow is not None:
                pago.mp_payment_id = int(preference_id) if preference_id and preference_id.isdigit() else None
                uow.add(pago)
            else:
                with VentasPagosTrazabilidadUnitOfWork(session) as update_uow:
                    db_pago = update_uow.pagos.get_by_external_reference(external_reference)
                    if db_pago:
                        db_pago.mp_payment_id = (
                            int(preference_id) if preference_id and preference_id.isdigit() else None
                        )
                        update_uow.add(db_pago)

            pago_read = PagoRead.model_validate(pago)
            return pago_read, init_point

        except Exception as exc:
            logger.exception("Error creating MP preference for pedido %s", pedido_id)
            # Return the Pago record anyway — it exists in DB with pending status.
            # The frontend can retry or fall back to EFECTIVO.
            return PagoRead.model_validate(pago), "#"

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

    @staticmethod
    def process_webhook(body: dict, background_tasks=None) -> dict:
        """Process a MercadoPago IPN webhook notification.

        Flow:
        1. Extract mp_payment_id from the webhook payload
        2. Fetch REAL payment status from MP API (never trust webhook data)
        3. Deduplicate by idempotency_key (ignore already-processed)
        4. Update Pago record
        5. If approved: advance Pedido to CONFIRMADO (auto-deducts stock)
        6. If rejected: keep Pedido in PENDIENTE (client can retry)

        Returns immediately with 200 to prevent MP retries.
        Heavy processing (API calls, DB writes) happens in background_tasks.

        Args:
            body: Parsed JSON body from the MP IPN POST request.
            background_tasks: Optional FastAPI BackgroundTasks instance.
                If provided, heavy processing is deferred to a background task.

        Returns:
            Dict with status and detail describing what was done.
        """
        import json as _json

        logger.info("MP webhook received: %s", _json.dumps(body, default=str))

        # ── Extract mp_payment_id from various MP notification formats ──
        mp_payment_id: int | None = None

        # Format 1: {"id": "12345", "topic": "payment", ...}
        raw_id = body.get("id")
        if raw_id and body.get("topic") == "payment":
            mp_payment_id = int(raw_id)

        # Format 2: {"data": {"id": "12345"}, "action": "payment.created", ...}
        if mp_payment_id is None:
            data_block = body.get("data", {})
            if data_block and isinstance(data_block, dict):
                raw_id = data_block.get("id")
                if raw_id:
                    try:
                        mp_payment_id = int(raw_id)
                    except (ValueError, TypeError):
                        pass

        if mp_payment_id is None:
            logger.warning("MP webhook: could not extract payment ID")
            return {"status": "received", "detail": "no payment id found"}

        # ── Fetch real status from MP API (never trust webhook data) ──
        payment_data = PagoService.get_payment_from_mp(mp_payment_id)
        if not payment_data:
            logger.warning(
                "MP webhook: could not fetch payment %s from MP API",
                mp_payment_id,
            )
            return {"status": "received", "detail": "could not fetch from MP"}

        mp_status = payment_data.get("status", "unknown")
        mp_status_detail = payment_data.get("status_detail")
        external_reference = payment_data.get("external_reference", "")
        idempotency_key = payment_data.get("idempotency_key", str(uuid.uuid4()))

        # ── Process in background to return 200 immediately ──
        from core.database import engine as _engine
        from sqlmodel import Session as _Session

        def _process():
            with _Session(_engine) as _session:
                repo = PagoRepository(_session)

                # Deduplicate: check if already processed with this key
                existing = repo.get_by_idempotency_key(idempotency_key)
                if existing and existing.mp_status in ("approved", "rejected"):
                    logger.info(
                        "MP webhook: duplicate ignored for idempotency_key=%s, status=%s",
                        idempotency_key, existing.mp_status,
                    )
                    return

                # Find existing Pago by external_reference
                pago = repo.get_by_external_reference(external_reference)
                if not pago:
                    logger.warning(
                        "MP webhook: no Pago found for external_reference=%s",
                        external_reference,
                    )
                    return

                # Update Pago status
                with VentasPagosTrazabilidadUnitOfWork(_session) as uow:
                    db_pago = uow.pagos.get_by_id(pago.id)
                    if not db_pago:
                        logger.warning("MP webhook: Pago %s not found in UoW", pago.id)
                        return

                    db_pago.mp_payment_id = mp_payment_id
                    db_pago.mp_status = mp_status
                    db_pago.mp_status_detail = mp_status_detail
                    uow.add(db_pago)

                    # ── If approved: advance Pedido to CONFIRMADO ──
                    if mp_status == "approved":
                        try:
                            from ..Pedido.service import PedidoService as _PedidoService

                            _PedidoService.confirmar_por_pago(
                                _session,
                                db_pago.pedido_id,
                            )
                            logger.info(
                                "MP webhook: pedido %s avanzado a CONFIRMADO",
                                db_pago.pedido_id,
                            )
                        except Exception as e:
                            logger.exception(
                                "MP webhook: error advancing pedido %s: %s",
                                db_pago.pedido_id, e,
                            )

                    logger.info(
                        "MP webhook: payment %s updated to %s for pedido %s",
                        mp_payment_id, mp_status, db_pago.pedido_id,
                    )

        if background_tasks is not None:
            background_tasks.add_task(_process)
        else:
            _process()

        return {"status": "received", "detail": "ok"}

    @staticmethod
    def get_payment_from_mp(mp_payment_id: int) -> dict | None:
        """Fetch payment details from MercadoPago API by MP payment ID.

        Used by the webhook to get the current status of a payment.

        Args:
            mp_payment_id: MercadoPago's internal payment ID from the notification.

        Returns:
            Dict with payment details (status, status_detail, etc.)
            or None if the payment cannot be fetched.
        """
        try:
            sdk = _get_mp_sdk()
            response = sdk.payment().get(mp_payment_id)
            if response.get("status") == 200:
                return response.get("response")
            logger.warning("MP get_payment returned status %s", response.get("status"))
            return None
        except Exception as exc:
            logger.exception("Error fetching MP payment %s", mp_payment_id)
            return None
