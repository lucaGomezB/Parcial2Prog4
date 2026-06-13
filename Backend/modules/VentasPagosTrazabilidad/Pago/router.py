"""
Pago router — API endpoints for payment processing.

Request flow: HTTP -> FastAPI (Pydantic validation) -> Router -> Service -> DB

Endpoints:
    - POST /pagos: Initiate a payment for an order (authenticated users).
    - GET /pagos/{pedido_id}: List payments for an order.
    - POST /pagos/webhook: Receive MercadoPago IPN notifications (no auth).

Prefix: /pagos
"""
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlmodel import Session
from typing import List
from pydantic import BaseModel

from core.database import get_session
from modules.IdentidadYAcceso.Auth.dependencies import get_current_user
from modules.IdentidadYAcceso.Usuario.models import Usuario
from .service import PagoService
from .schemas import PagoRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pagos", tags=["Pagos"])


class InitPaymentRequest(BaseModel):
    """Request body for initiating a MercadoPago payment."""
    pedido_id: int


class InitPaymentResponse(BaseModel):
    """Response for the payment initiation endpoint.

    Returns the created payment record and the MercadoPago checkout URL
    for redirect-based payment integration.
    """
    pago: PagoRead
    init_point: str


@router.post("/", response_model=InitPaymentResponse,
             status_code=status.HTTP_201_CREATED)
def init_payment(
    data: InitPaymentRequest,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """POST /pagos — Initiate a MercadoPago payment for an order.

    Creates a pending Pago record, then creates a checkout preference
    in MercadoPago. Returns the payment record and the checkout URL
    (init_point) where the user should be redirected.

    Requires an authenticated user (any role).
    """
    try:
        pago_read, init_point = PagoService.init_mp_payment(session, data.pedido_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return InitPaymentResponse(pago=pago_read, init_point=init_point)


@router.get("/{pedido_id}", response_model=List[PagoRead])
def list_pagos_by_pedido(
    pedido_id: int,
    session: Session = Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """GET /pagos/{pedido_id} — List all payments for a given order.

    ADMIN/PEDIDOS can see any order's payments; regular users can only
    see payments for their own orders. Returns payments ordered by
    creation date (newest first).
    """
    from ..Pedido.service import PedidoService as _PedidoService
    pedido = _PedidoService.get_by_id(session, pedido_id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if not any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles):
        if pedido.usuario_id != current_user.id:
            raise HTTPException(status_code=403, detail="No tienes permiso para ver este pedido")

    return PagoService.get_pagos_by_pedido(session, pedido_id)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook_receiver(request: Request, background_tasks: BackgroundTasks):
    """POST /pagos/webhook — MercadoPago IPN webhook receiver.

    Responds with 200 OK immediately to prevent MP retries.
    Actual processing (API verification, DB updates) runs in background.

    Receives payment status notifications from MercadoPago's IPN system.
    This endpoint has NO authentication — security is through the
    external_reference lookup and idempotency_key deduplication.

    All processing logic is delegated to PagoService.process_webhook().
    The router ONLY parses the request and returns the response.
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    result = PagoService.process_webhook(body, background_tasks=background_tasks)
    return result
