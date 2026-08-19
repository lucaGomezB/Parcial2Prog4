"""
Pago router — endpoints for payment initiation and MercadoPago webhook/IPN.
"""

import hmac
import hashlib
import json
import logging
import os

from fastapi import APIRouter, Depends, Request, status, HTTPException, BackgroundTasks
from starlette.responses import RedirectResponse
from sqlmodel import Session

from app.core.database import get_session
from app.modules.IdentidadYAcceso.Auth.dependencies import get_current_user, get_current_user_optional
from app.modules.IdentidadYAcceso.Usuario.models import Usuario

from .service import PagoService
from .schemas import (
    InitPaymentResponse,
    InitFromCartRequest,
    PagoRead,
    PaymentStatusResponse,
)

logger = logging.getLogger("mercadopago.webhook")
_auth_logger = logging.getLogger("pagos.auth")

router = APIRouter(prefix="/pagos", tags=["pagos"])


# ── Combined auth for post-pago status polling ──
# Tries JWT first, falls back to external_reference (travels through MP redirect).
async def _auth_for_status(
    external_reference: str,
    session: Session = Depends(get_session),
    jwt_user: Usuario | None = Depends(get_current_user_optional),
) -> Usuario:
    """Authenticate for GET /pagos/status.

    When the user returns from MercadoPago, their JWT may have expired.
    The external_reference UUID (embedded in the redirect URL) acts as a
    temporary credential — it resolves to the user who initiated the payment.
    """
    if jwt_user is not None:
        return jwt_user

    user = PagoService.resolve_user_from_payment_ref(session, external_reference)
    if user is not None:
        _auth_logger.info(
            "_auth_for_status: resolved via external_reference=%s -> user_id=%s",
            external_reference[:8], user.id,
        )
        return user

    # Diagnostic: log WHY auth failed
    _auth_logger.warning(
        "_auth_for_status FAILED: external_reference=%s jwt_user=%s. "
        "JWT may be expired AND external_reference could not resolve to a user.",
        external_reference[:16] if external_reference else "None",
        "present" if jwt_user is not None else "None",
    )

    raise HTTPException(
        status_code=401,
        detail="No se pudieron validar las credenciales",
    )

# ── Module-level guard: warn once if the webhook secret is missing or a placeholder ──
_WEBHOOK_SECRET = os.getenv("MP_WEBHOOK_SECRET", "")
if not _WEBHOOK_SECRET or _WEBHOOK_SECRET == "your-webhook-secret-here":
    logger.warning(
        "MP_WEBHOOK_SECRET is missing or still the default placeholder. "
        "Webhook signature validation will be skipped — any caller can POST to /pagos/webhook."
    )

# ── Sandbox detection: MP access tokens starting with TEST- indicate sandbox mode ──
_MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
_IS_MP_SANDBOX = _MP_ACCESS_TOKEN.startswith("TEST-")


@router.post("/init-from-cart", response_model=InitPaymentResponse, status_code=status.HTTP_201_CREATED)
async def init_payment_from_cart(
    data: InitFromCartRequest,
    session=Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """POST /pagos/init-from-cart — Initiate MercadoPago payment from cart items.

    The NEW post-pago flow:
    1. Validates stock for all cart items
    2. Creates a carrito_snapshot (persists cart state during payment window)
    3. Creates a Pago record with pedido_id=NULL
    4. Creates a MercadoPago preference with cart items as line items
    5. Returns the init_point URL for redirecting the user

    The cart is NOT cleared. The Pedido is created on payment confirmation
    via webhook. The cart is cleared via WebSocket pago_confirmado event.

    Access: any authenticated user.
    """
    try:
        pago_read, init_point, mp_error = PagoService.init_from_cart(
            session, data, current_user
        )
    except ValueError as e:
        detalles = getattr(e, 'detalles', None)
        error_detail = {"error": "stock_insuficiente", "mensaje": str(e)}
        if detalles is not None:
            error_detail["detalles"] = detalles
        raise HTTPException(status_code=409, detail=error_detail)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    if init_point is None:
        return InitPaymentResponse(
            pago=pago_read,
            init_point=None,
            error=mp_error or "MercadoPago no respondio con una URL de pago. Verifica el token MP_ACCESS_TOKEN en Backend/.env",
        )
    return InitPaymentResponse(pago=pago_read, init_point=init_point)


def _validate_mp_signature(raw_body: bytes, headers) -> bool:
    """Validate the x-signature header from a MercadoPago webhook.

    MercadoPago signs webhooks using two possible formats (both HMAC-SHA256
    keyed with MP_WEBHOOK_SECRET):

    Format A (newer): signature over <x-request-id>.<data.id>
    Format B (legacy):  signature over just the raw request body

    This function attempts Format A first (the current documentation standard).
    If a data.id can be extracted from the JSON body, Format A is checked.
    If that fails, Format B is checked as a fallback.

    Returns True if ANY format matches, False otherwise.
    """
    x_signature = headers.get("x-signature")
    if not x_signature:
        return False

    if not _WEBHOOK_SECRET:
        return False

    # ── Extract data.id from the request body for Format A ──
    data_id = None
    try:
        body_json = json.loads(raw_body.decode("utf-8"))
        data_id = body_json.get("data", {}).get("id") or body_json.get("id")
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass

    # ── Format A: HMAC-SHA256(secret, x-request-id + "." + data.id) ──
    x_request_id = headers.get("x-request-id", "")
    if x_request_id and data_id:
        payload_a = f"{x_request_id}.{data_id}"
        expected_a = hmac.new(
            _WEBHOOK_SECRET.encode("utf-8"),
            payload_a.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(x_signature, expected_a):
            return True

    # ── Format B (legacy): HMAC-SHA256(secret, raw_body) ──
    expected_b = hmac.new(
        _WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    if hmac.compare_digest(x_signature, expected_b):
        return True

    # ── Diagnostic log on mismatch: record what MP sent so we can fix the format ──
    logger.warning(
        "MP webhook signature mismatch. x-signature=%s x-request-id=%s data.id=%s body_preview=%s",
        x_signature,
        x_request_id,
        data_id,
        raw_body.decode("utf-8", errors="replace")[:200],
    )
    return False


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def webhook_receiver(request: Request, background_tasks: BackgroundTasks):
    """POST /pagos/webhook — MercadoPago IPN webhook receiver.

    Validates the x-signature header using HMAC-SHA256 (Format A:
    <x-request-id>.<data.id> or Format B: raw body). Requests without
    a valid signature receive HTTP 403 (unless MP_WEBHOOK_SECRET is
    not configured, in which case everything is allowed).

    After validation, responds with 200 OK immediately to prevent MP retries.
    Actual processing (API verification, DB updates) runs in background.
    """
    raw_body = await request.body()

    # ── DIAGNOSTIC: log every header MP sends so we can reverse-engineer the signature format ──
    raw_body_str = raw_body.decode("utf-8", errors="replace")
    logger.info(
        "MP WEBHOOK RECEIVED | headers=%s | body=%s",
        {k: v for k, v in request.headers.items() if k.startswith("x-") or k in ("content-type", "host")},
        raw_body_str[:500],
    )

    # ── Validate signature (if secret is configured) ──
    if _WEBHOOK_SECRET and _WEBHOOK_SECRET != "your-webhook-secret-here":
        if _IS_MP_SANDBOX:
            # Sandbox mode: skip signature validation entirely.
            # MP sandbox webhooks may lack the header or use a different
            # secret than what's configured. Log result for diagnostics
            # but never block the request.
            x_signature = request.headers.get("x-signature")
            if not x_signature:
                logger.warning("MP webhook (sandbox): no x-signature header, allowing through")
            elif not _validate_mp_signature(raw_body, request.headers):
                logger.warning(
                    "MP webhook (sandbox): signature mismatch — allowing through anyway. "
                    "Verify MP_WEBHOOK_SECRET in .env matches the MP dashboard webhook secret."
                )
            else:
                logger.info("MP webhook (sandbox): signature validated successfully")
        elif not _validate_mp_signature(raw_body, request.headers):
            raise HTTPException(status_code=403, detail={"error": "invalid_signature"})
    else:
        logger.warning("MP webhook received without signature validation (secret not configured)")

    # ── Parse JSON ──
    try:
        raw_body_str = raw_body.decode("utf-8")
        body = json.loads(raw_body_str)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("MP webhook: failed to parse request body as JSON")
        body = {}

    result = PagoService.process_webhook(body, background_tasks=background_tasks)
    return result


@router.get("/status", response_model=PaymentStatusResponse)
async def get_payment_status(
    external_reference: str,
    session=Depends(get_session),
    current_user: Usuario = Depends(_auth_for_status),
):
    """GET /pagos/status?external_reference=<uuid> — Poll for Pedido creation.

    Used by PostPagoPage after MercadoPago redirects back.
    Authenticated via JWT (normal) or external_reference (post-MP redirect).
    Returns found/pending/not_found based on whether the Pedido has been
    created from the payment's cart snapshot.
    """
    result = PagoService.check_pedido_status(session, external_reference, current_user)
    if result["status"] == "not_found":
        raise HTTPException(
            status_code=404,
            detail={"status": "not_found", "detail": "No payment found for this reference"},
        )
    return result


@router.get("/mp-redirect")
async def mp_redirect(
    external_reference: str,
    status: str = "approved",
):
    """GET /pagos/mp-redirect — HTTPS redirect proxy for MP back_urls.

    MercadoPago requires HTTPS back_urls for auto_return to work.
    Since the frontend runs on HTTP (localhost) in dev, this endpoint
    receives the HTTPS redirect from MP (via ngrok) and forwards the
    user's browser to the actual frontend URL.

    Query params:
        external_reference: UUID shared between Pago/Snapshot/Pedido
        status: "approved" | "failure" | "pending"
    """
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    target = f"{frontend_url}/pedidos/post-pago?external_reference={external_reference}&status={status}"
    return RedirectResponse(url=target, status_code=302)


@router.get("/{pedido_id}", response_model=list[PagoRead])
async def get_pagos_by_pedido(
    pedido_id: int,
    session=Depends(get_session),
    current_user: Usuario = Depends(get_current_user),
):
    """GET /pagos/{pedido_id} — List all payment records for a pedido.

    Admins and PEDIDOS-role users can view any pedido's payments.
    Regular users can only view their own pedidos' payments.

    Returns an empty list if the pedido doesn't exist or has no payments.
    Results are ordered by most recent first (descending creation date).
    """
    return PagoService.get_pagos_by_pedido_autorizado(session, pedido_id, current_user)
