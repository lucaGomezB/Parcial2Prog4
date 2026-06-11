"""
Pago router — API endpoints for payment processing.

Request flow: HTTP -> FastAPI (Pydantic validation) -> Router -> Service -> DB

Endpoints:
    - POST /pagos: Initiate a payment for an order (authenticated users).
    - GET /pagos/{pedido_id}: List payments for an order (ADMIN/PEDIDOS).
    - POST /pagos/webhook: Receive MercadoPago IPN notifications (no auth).

Prefix: /pagos
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from pydantic import BaseModel

from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import require_roles, get_current_user
from modules.IdentidadYAcceso.Usuario.models import Usuario
from .service import PagoService
from .schemas import PagoRead

router = APIRouter(prefix="/pagos", tags=["Pagos"])


class InitPaymentRequest(BaseModel):
    """Request body for initiating a MercadoPago payment."""
    pedido_id: int


class InitPaymentResponse(BaseModel):
    """Response for the payment initiation endpoint.

    Returns the created payment record and a placeholder checkout URL
    for redirect-based MercadoPago integration.
    """
    pago: PagoRead
    init_point: str = "#"


@router.post("/", response_model=InitPaymentResponse,
             status_code=status.HTTP_201_CREATED)
def init_payment(
    data: InitPaymentRequest,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """POST /pagos — Initiate a MercadoPago payment for an order.

    Creates a pending Pago record with UUIDs for external_reference
    and idempotency_key. Returns the payment record and a placeholder
    checkout URL (the actual MP API call will be added in a future
    integration).

    Requires an authenticated user (any role).
    """
    try:
        pago = PagoService.init_mp_payment(session, data.pedido_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return InitPaymentResponse(pago=pago)


@router.get("/{pedido_id}", response_model=List[PagoRead],
            dependencies=[Depends(require_roles(["ADMIN", "PEDIDOS"]))])
def list_pagos_by_pedido(
    pedido_id: int,
    session: Session = Depends(get_session),
):
    """GET /pagos/{pedido_id} — List all payments for a given order.

    Returns payments ordered by creation date (newest first).
    Requires ADMIN or PEDIDOS role.
    """
    return PagoService.get_pagos_by_pedido(session, pedido_id)


class WebhookPayload(BaseModel):
    """Generic MercadoPago IPN webhook payload.

    In production, this will contain MP's notification data.
    For now, it's a placeholder that accepts any JSON body.
    """
    pass


@router.post("/webhook", status_code=status.HTTP_200_OK)
def webhook_receiver(
    data: WebhookPayload,
    session: Session = Depends(get_session),
):
    """POST /pagos/webhook — MercadoPago IPN webhook receiver.

    Receives payment status updates from MercadoPago's IPN system.
    This endpoint has NO authentication — security is through
    signature verification (to be implemented).

    Currently a placeholder that returns 200 OK.
    """
    # TODO: Verify MP-Webhook-Signature header
    # TODO: Look up payment by external_reference or mp_payment_id
    # TODO: Update payment status via PagoService.update_pago_status()
    return {"status": "received"}
