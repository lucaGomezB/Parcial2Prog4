"""
Pago service — MercadoPago payment business logic.

This service provides:
    - init_from_cart: Creates a preference in MercadoPago from cart items,
      returns the checkout init_point URL. Creates Pago (pedido_id=NULL) and
      cart_snapshot. This is the NEW post-pago flow.
    - init_mp_payment: LEGACY — replaced by init_from_cart. Kept for reference.
    - update_pago_status: Updates an existing Pago record from webhook data.
    - get_pagos_by_pedido: Lists all payments for an order (read-only).
    - get_payment_from_mp: Fetches payment details from MP API by MP payment ID.
    - process_webhook: Handles MP IPN. On approved, creates Pedido from snapshot.

PATTERN: Write operations use VentasPagosTrazabilidadUnitOfWork for atomicity.
Read operations use the repository directly (no UoW) to avoid commit/expire.
"""
import hashlib
import json as _json
import logging
import os
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

import mercadopago
from fastapi import HTTPException, status
from mercadopago.config.request_options import RequestOptions
from sqlmodel import Session

from .models import Pago
from .repository import PagoRepository
from .schemas import PagoRead, InitFromCartRequest
from ..uow import VentasPagosTrazabilidadUnitOfWork
from ..Pedido.service import PedidoService
from ..CarritoSnapshot.models import CarritoSnapshot
from app.core.dependencies import fire_broadcast, fire_broadcast_admin, fire_broadcast_user, get_ws_manager
from app.core.routing import get_or_404

logger = logging.getLogger(__name__)

# ── MercadoPago SDK singleton ──
_sdk: mercadopago.SDK | None = None
_cached_token: str | None = None


def _get_mp_sdk() -> mercadopago.SDK:
    """Return a MercadoPago SDK instance.

    Reads MP_ACCESS_TOKEN from environment. The SDK is re-created when
    the token changes (supports hot-reload of .env without restart).
    """
    global _sdk, _cached_token
    token = os.getenv("MP_ACCESS_TOKEN", "")
    if not token or "000000" in token:
        raise RuntimeError(
            "MP_ACCESS_TOKEN no configurado o es un placeholder. "
            "Configuralo en Backend/.env con un token real de MercadoPago."
        )
    if _sdk is None or token != _cached_token:
        _sdk = mercadopago.SDK(token)
        _cached_token = token
    return _sdk


# ── Ngrok / webhook base URL ──
def _get_webhook_base_url() -> str:
    return os.getenv("NGROK_URL", "http://localhost:8000").rstrip("/")


# ── Frontend base URL for redirect back_urls ──
def _get_frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def _cart_fingerprint(data: InitFromCartRequest, usuario_id: int) -> str:
    """Generate a deterministic fingerprint from cart data for idempotency.

    Uses SHA256 over the serialized cart + user to detect duplicate init_from_cart
    requests (e.g., double-clicks, retries before redirect).
    """
    raw = _json.dumps(
        {
            "usuario_id": usuario_id,
            "items": sorted(
                [
                    {
                        "producto_id": i.producto_id,
                        "cantidad": i.cantidad,
                        "precio": str(i.precio),
                        "ingredientes_excluidos": sorted(i.ingredientes_excluidos or []),
                    }
                    for i in data.items
                ],
                key=lambda x: x["producto_id"],
            ),
            "forma_pago_codigo": data.forma_pago_codigo,
            "subtotal": str(data.subtotal),
            "costo_envio": str(data.costo_envio),
            "descuento": str(data.descuento),
            "direccion_id": data.direccion_id,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


class PagoService:
    """Business logic for MercadoPago payment operations."""

    # ──────────────────────────────────────────────────────────────────────
    # NEW: init_from_cart — the post-pago flow
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def init_from_cart(
        session: Session,
        data: InitFromCartRequest,
        usuario,
    ) -> tuple[PagoRead, Optional[str], Optional[str]]:
        """Create a MercadoPago checkout preference from cart items.

        This is the NEW post-pago flow:
        1. Validate stock for all items
        2. Generate external_reference and idempotency_key (UUIDs)
        3. Create carrito_snapshot (cart preserved during payment window)
        4. Create Pago record with pedido_id=NULL
        5. Create MP preference with cart items as line items
        6. Return (PagoRead, init_point, mp_error)

        Returns:
            Tuple of (PagoRead, init_point_url, mp_error_or_None).
            init_point is None if the MP SDK call fails (Pago + snapshot
            still exist in DB). mp_error is a string describing the MP
            error or None on success.
        """
        from app.modules.CatalogoDeProductos.Producto.repository import ProductoRepository

        # ── Step 1: Validate stock ──
        producto_repo = ProductoRepository(session)
        stock_failures = []
        for item in data.items:
            producto = producto_repo.get_by_id(item.producto_id)
            if not producto:
                raise ValueError(f"Producto ID {item.producto_id} no encontrado")
            if producto.es_producto_terminado:
                stock_disp = producto.stock_manual or 0
            else:
                stock_disp = producto_repo.compute_derived_stock(item.producto_id)
                producto.stock_cantidad = stock_disp
                session.add(producto)

            if stock_disp < item.cantidad:
                stock_failures.append({
                    "producto_id": producto.id,
                    "nombre_producto": producto.nombre,
                    "cantidad_solicitada": item.cantidad,
                    "stock_disponible": stock_disp,
                })
        if stock_failures:
            error = ValueError("Stock insuficiente para uno o mas productos")
            error.detalles = stock_failures
            raise error

        # ── Step 2: Idempotency — detect duplicate init ──
        fingerprint = _cart_fingerprint(data, usuario.id)

        # Check for existing Pago with same idempotency key (double-click guard).
        # ONLY match Pagos that have NOT yet resulted in a Pedido (pedido_id=NULL).
        # If the user is making a new purchase with the same cart contents as a
        # previous completed order, generate a fresh fingerprint so the new Pago
        # gets a unique idempotency_key (avoiding the UNIQUE constraint on
        # idempotency_key in the pago table).
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            existing_pago = uow.pagos.get_by_idempotency_key(fingerprint)
            if existing_pago is not None and existing_pago.pedido_id is not None:
                # Old Pago already resulted in a Pedido — this is a fresh purchase,
                # not a retry. Generate a unique fingerprint.
                fingerprint = f"{fingerprint}-{uuid.uuid4().hex[:8]}"
                existing_pago = None  # force new Pago creation below

            if existing_pago is not None:
                mp_pid = existing_pago.mp_payment_id
                if mp_pid is not None:
                    # Already paid — try to get a fresh init_point
                    try:
                        sdk = _get_mp_sdk()
                        mp_pago = sdk.payment().get(mp_pid)
                        mp_data = mp_pago.get("response", {})
                        init_point = (
                            mp_data.get("sandbox_init_point")
                            or mp_data.get("init_point")
                        )
                        if init_point:
                            pago_read = PagoRead.model_validate(existing_pago)
                            return pago_read, init_point, None
                    except Exception:
                        pass  # MP lookup failed, but Pago exists

                # mp_payment_id is None (preference-only, not yet paid).
                # Re-create the MP preference WITHOUT creating a new Pago
                # record — that would violate the UNIQUE constraint on
                # external_reference. Reuse existing Pago + Snapshot.
                logger.info(
                    "Retry init_from_cart for fingerprint=%s: re-creating MP "
                    "preference for existing Pago id=%s external_reference=%s",
                    fingerprint, existing_pago.id, existing_pago.external_reference,
                )
                # Build preference items from cart data
                retry_preference_items = []
                for item in data.items:
                    retry_preference_items.append({
                        "title": item.nombre,
                        "quantity": item.cantidad,
                        "unit_price": float(item.precio),
                        "currency_id": "ARS",
                        "category_id": "food",
                    })
                # Add shipping line item when costo_envio > 0
                if data.costo_envio > 0:
                    retry_preference_items.append({
                        "title": "Costo de envío",
                        "quantity": 1,
                        "unit_price": float(data.costo_envio),
                        "currency_id": "ARS",
                    })
                # Calculate total
                retry_total = data.subtotal - data.descuento + data.costo_envio
                if retry_total < 0:
                    retry_total = Decimal("0.00")
                # Build preference_data
                frontend_url = _get_frontend_url()
                webhook_base = _get_webhook_base_url()
                ext_ref = existing_pago.external_reference

                # ── Recreate the CarritoSnapshot if it expired / was deleted ──
                # The snapshot is the ONLY source of cart items used by the
                # webhook to build the Pedido. On retry, the previous snapshot
                # may have been cleaned up by TTL expiry; recreate it with the
                # SAME external_reference so the webhook can find it later.
                if uow.snapshots.get_by_external_reference(ext_ref) is None:
                    snapshot_items = []
                    for item in data.items:
                        snapshot_items.append({
                            "producto_id": item.producto_id,
                            "nombre": item.nombre,
                            "precio": float(item.precio),
                            "cantidad": item.cantidad,
                            "ingredientes_excluidos": item.ingredientes_excluidos,
                        })
                    snapshot = CarritoSnapshot(
                        usuario_id=usuario.id,
                        items=snapshot_items,
                        direccion_id=data.direccion_id,
                        direccion_snapshot=None,
                        forma_pago_codigo="MERCADOPAGO",
                        costo_envio=data.costo_envio,
                        subtotal=data.subtotal,
                        total=retry_total,
                        external_reference=ext_ref,
                        notas=data.notas,
                    )
                    if data.direccion_id is not None:
                        from app.modules.IdentidadYAcceso.uow import IdentidadYAccesoUnitOfWork

                        dir_repo = IdentidadYAccesoUnitOfWork(session).direcciones
                        direccion = dir_repo.get_by_id(data.direccion_id)
                        if direccion:
                            snapshot.direccion_snapshot = {
                                "linea1": getattr(direccion, "linea1", None),
                                "linea2": getattr(direccion, "linea2", None),
                                "ciudad": getattr(direccion, "ciudad", None),
                            }
                    uow.snapshots.create(snapshot)
                    logger.info(
                        "Retry init_from_cart: recreated expired snapshot for "
                        "external_reference=%s", ext_ref,
                    )

                # ── Build back_urls ──
                # When ngrok provides HTTPS, use the mp-redirect proxy so auto_return works.
                # Otherwise fall back to direct HTTP URLs without auto_return.
                if webhook_base.startswith("https"):
                    back_urls = {
                        "success": f"{webhook_base}/api/v1/pagos/mp-redirect?external_reference={ext_ref}&status=approved",
                        "failure": f"{webhook_base}/api/v1/pagos/mp-redirect?external_reference={ext_ref}&status=failure",
                        "pending": f"{webhook_base}/api/v1/pagos/mp-redirect?external_reference={ext_ref}&status=pending",
                    }
                else:
                    back_urls = {
                        "success": f"{frontend_url}/pedidos/post-pago?external_reference={ext_ref}&status=approved",
                        "failure": f"{frontend_url}/carrito",
                        "pending": f"{frontend_url}/pedidos/post-pago?external_reference={ext_ref}&status=approved",
                    }

                preference_data = {
                    "items": retry_preference_items,
                    "external_reference": ext_ref,
                    "back_urls": back_urls,
                }

                preference_data["statement_descriptor"] = os.getenv("MP_STATEMENT_DESCRIPTOR", "FoodStore")

                # auto_return only safe with HTTPS back_urls (MP rejects HTTP)
                if webhook_base.startswith("https"):
                    preference_data["auto_return"] = "approved"

                if usuario:
                    preference_data["payer"] = {
                        "name": usuario.nombre,
                        "email": usuario.email,
                    }
                allow_http = os.getenv("MP_ALLOW_HTTP_WEBHOOK", "").lower() == "true"
                if webhook_base and (webhook_base.startswith("https") or allow_http):
                    if allow_http and not webhook_base.startswith("https"):
                        logger.info("notification_url set with HTTP (dev mode)")
                    preference_data["notification_url"] = f"{webhook_base}/api/v1/pagos/webhook"

                retry_idempotency_key = f"{fingerprint}-retry-{uuid.uuid4()}"
                try:
                    sdk = _get_mp_sdk()
                    preference_response = sdk.preference().create(
                        preference_data,
                        RequestOptions(
                            custom_headers={"X-Idempotency-Key": retry_idempotency_key}
                        ),
                    )
                    response_data = preference_response.get("response", {})
                    if preference_response.get("status") not in (200, 201):
                        mp_message = response_data.get("message", "unknown error")
                        mp_status = preference_response.get("status", "?")
                        logger.error("MP preference creation failed [status=%s]: %s", mp_status, mp_message)
                        pago_read = PagoRead.model_validate(existing_pago)
                        return pago_read, None, f"MP[{mp_status}]: {mp_message}"
                    init_point = (
                        response_data.get("sandbox_init_point")
                        or response_data.get("init_point")
                    )
                    pago_read = PagoRead.model_validate(existing_pago)
                    return pago_read, init_point, None
                except Exception as exc:
                    logger.exception("Error re-creating MP preference for existing Pago %s", existing_pago.id)
                    pago_read = PagoRead.model_validate(existing_pago)
                    return pago_read, None, str(exc)

        # ── Step 3: Generate external_reference and idempotency_key ──
        external_reference = str(uuid.uuid4())
        idempotency_key = fingerprint

        # ── Step 4: Calculate total ──
        total = data.subtotal - data.descuento + data.costo_envio
        if total < 0:
            total = Decimal("0.00")

        # ── Step 5: Build items JSON for snapshot ──
        snapshot_items = []
        preference_items = []
        for item in data.items:
            snapshot_items.append({
                "producto_id": item.producto_id,
                "nombre": item.nombre,
                "precio": float(item.precio),
                "cantidad": item.cantidad,
                "ingredientes_excluidos": item.ingredientes_excluidos,
            })
            preference_items.append({
                "title": item.nombre,
                "quantity": item.cantidad,
                "unit_price": float(item.precio),
                "currency_id": "ARS",
                "category_id": "food",
            })

        # Add shipping line item when costo_envio > 0
        if data.costo_envio > 0:
            preference_items.append({
                "title": "Costo de envío",
                "quantity": 1,
                "unit_price": float(data.costo_envio),
                "currency_id": "ARS",
            })

        # ── Step 6: Create snapshot + Pago in a single UoW ──
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            # Create the cart snapshot
            snapshot = CarritoSnapshot(
                usuario_id=usuario.id,
                items=snapshot_items,
                direccion_id=data.direccion_id,
                direccion_snapshot=None,  # frozen address built below
                forma_pago_codigo="MERCADOPAGO",
                costo_envio=data.costo_envio,
                subtotal=data.subtotal,
                total=total,
                external_reference=external_reference,
                notas=data.notas,
            )

            # Freeze address if provided
            if data.direccion_id is not None:
                from app.modules.IdentidadYAcceso.uow import IdentidadYAccesoUnitOfWork

                dir_repo = IdentidadYAccesoUnitOfWork(session).direcciones
                direccion = dir_repo.get_by_id(data.direccion_id)
                if direccion:
                    snapshot.direccion_snapshot = {
                        "linea1": getattr(direccion, "linea1", None),
                        "linea2": getattr(direccion, "linea2", None),
                        "ciudad": getattr(direccion, "ciudad", None),
                    }

            uow.snapshots.create(snapshot)

            # Create the Pago record (pedido_id=NULL)
            pago = Pago(
                pedido_id=None,
                mp_status="pending",
                mp_status_detail=None,
                mp_payment_id=None,
                external_reference=external_reference,
                idempotency_key=idempotency_key,
                transaction_amount=total,
                payment_method_id=None,
            )
            uow.pagos.create(pago)

            # ── Step 7: Create preference in MercadoPago ──
            try:
                sdk = _get_mp_sdk()
                frontend_url = _get_frontend_url()
                webhook_base = _get_webhook_base_url()

                # ── Build back_urls ──
                # When ngrok provides HTTPS, use the mp-redirect proxy so auto_return works.
                # Otherwise fall back to direct HTTP URLs without auto_return.
                if webhook_base.startswith("https"):
                    back_urls = {
                        "success": f"{webhook_base}/api/v1/pagos/mp-redirect?external_reference={external_reference}&status=approved",
                        "failure": f"{webhook_base}/api/v1/pagos/mp-redirect?external_reference={external_reference}&status=failure",
                        "pending": f"{webhook_base}/api/v1/pagos/mp-redirect?external_reference={external_reference}&status=pending",
                    }
                else:
                    back_urls = {
                        "success": f"{frontend_url}/pedidos/post-pago?external_reference={external_reference}&status=approved",
                        "failure": f"{frontend_url}/carrito",
                        "pending": f"{frontend_url}/pedidos/post-pago?external_reference={external_reference}&status=approved",
                    }

                preference_data = {
                    "items": preference_items,
                    "external_reference": external_reference,
                    "back_urls": back_urls,
                }

                preference_data["statement_descriptor"] = os.getenv("MP_STATEMENT_DESCRIPTOR", "FoodStore")

                # auto_return only safe with HTTPS back_urls (MP rejects HTTP)
                if webhook_base.startswith("https"):
                    preference_data["auto_return"] = "approved"

                if usuario:
                    preference_data["payer"] = {
                        "name": usuario.nombre,
                        "email": usuario.email,
                    }

                allow_http = os.getenv("MP_ALLOW_HTTP_WEBHOOK", "").lower() == "true"
                if webhook_base and (webhook_base.startswith("https") or allow_http):
                    if allow_http and not webhook_base.startswith("https"):
                        logger.info("notification_url set with HTTP (dev mode)")
                    preference_data["notification_url"] = f"{webhook_base}/api/v1/pagos/webhook"

                preference_response = sdk.preference().create(
                    preference_data,
                    RequestOptions(
                        custom_headers={"X-Idempotency-Key": idempotency_key}
                    ),
                )
                response_data = preference_response.get("response", {})

                if preference_response.get("status") not in (200, 201):
                    mp_message = preference_response.get("response", {}).get("message", "unknown error")
                    mp_status = preference_response.get("status", "?")
                    logger.error(
                        "MP preference creation failed [status=%s]: %s",
                        mp_status, mp_message,
                    )
                    logger.error("Full MP response: %s", preference_response)
                    pago_read = PagoRead.model_validate(pago)
                    return pago_read, None, f"MP[{mp_status}]: {mp_message}"

                init_point = (
                    response_data.get("sandbox_init_point")
                    or response_data.get("init_point")
                    or None
                )
                preference_id = response_data.get("id")

                # Note: MP preference IDs contain hyphens (e.g. "2162743739-f86d9b72-...")
                # and cannot be stored in mp_payment_id (an int column).
                # mp_payment_id is reserved for the numeric payment ID received via webhook.

                pago_read = PagoRead.model_validate(pago)
                return pago_read, init_point, None

            except Exception as exc:
                logger.exception("Error creating MP preference from cart for user %s", usuario.id)
                pago_read = PagoRead.model_validate(pago)
                return pago_read, None, str(exc)

    # ──────────────────────────────────────────────────────────────────────
    # LEGACY: init_mp_payment — kept for backward-compat, deprecated
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def init_mp_payment(
        session: Session,
        pedido_id: int,
        uow: Optional[VentasPagosTrazabilidadUnitOfWork] = None,
    ) -> tuple[PagoRead, Optional[str]]:
        """DEPRECATED: Use init_from_cart instead.

        Create a MercadoPago checkout preference from an existing pedido_id.
        Kept for backward compatibility with the PedidosPage retry button.

        Steps:
            1. Fetch the Pedido to validate existence and get the total
            2. Check if a Pago already exists for this pedido (idempotent)
            3. Generate external_reference and idempotency_key as UUIDs
            4. Create the Pago record in DB
            5. Create a preference in MercadoPago via SDK
            6. Return (PagoRead, init_point) tuple

        Returns:
            Tuple of (PagoRead, init_point_url). init_point is None if
            the MP SDK call fails (payment record still exists in DB).
        """
        # Validate the pedido exists and get its total
        pedido = PedidoService.get_by_id(session, pedido_id)
        if not pedido:
            raise ValueError(f"Pedido {pedido_id} no encontrado")

        # ── Idempotency ──
        pago_repo = PagoRepository(session)
        existing_pago = pago_repo.get_pending_or_approved(pedido_id)
        if existing_pago:
            logger.info(
                "Duplicate Pago prevented for pedido %s: existing Pago id=%s, status=%s",
                pedido_id, existing_pago.id, existing_pago.mp_status,
            )
            return PagoRead.model_validate(existing_pago), None

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
            uow.pagos.create(pago)
        else:
            with VentasPagosTrazabilidadUnitOfWork(session) as new_uow:
                new_uow.pagos.create(pago)

        # ── Create the preference in MercadoPago ──
        try:
            sdk = _get_mp_sdk()
            webhook_base = _get_webhook_base_url()
            frontend_url = _get_frontend_url()

            # ── Build back_urls ──
            # When ngrok provides HTTPS, use the mp-redirect proxy so auto_return works.
            # Otherwise fall back to direct HTTP URLs without auto_return.
            if webhook_base.startswith("https"):
                back_urls = {
                    "success": f"{webhook_base}/api/v1/pagos/mp-redirect?external_reference={external_reference}&status=approved",
                    "failure": f"{webhook_base}/api/v1/pagos/mp-redirect?external_reference={external_reference}&status=failure",
                    "pending": f"{webhook_base}/api/v1/pagos/mp-redirect?external_reference={external_reference}&status=pending",
                }
            else:
                back_urls = {
                    "success": f"{frontend_url}/pedidos/{pedido_id}",
                    "failure": f"{frontend_url}/carrito",
                    "pending": f"{frontend_url}/pedidos/{pedido_id}",
                }

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
                "back_urls": back_urls,
            }

            # auto_return only safe with HTTPS back_urls (MP rejects HTTP)
            if webhook_base.startswith("https"):
                preference_data["auto_return"] = "approved"

            if pedido.usuario:
                preference_data["payer"] = {
                    "name": pedido.usuario.nombre,
                    "email": pedido.usuario.email,
                }

            allow_http = os.getenv("MP_ALLOW_HTTP_WEBHOOK", "").lower() == "true"
            if webhook_base and (webhook_base.startswith("https") or allow_http):
                if allow_http and not webhook_base.startswith("https"):
                    logger.info("notification_url set with HTTP (dev mode)")
                preference_data["notification_url"] = f"{webhook_base}/api/v1/pagos/webhook"

            preference_response = sdk.preference().create(
                preference_data,
                RequestOptions(
                    custom_headers={"X-Idempotency-Key": idempotency_key}
                ),
            )
            response_data = preference_response.get("response", {})

            if preference_response.get("status") not in (200, 201):
                logger.error(
                    "MP preference creation failed: %s",
                    preference_response.get("response", {}).get("message", "unknown error"),
                )
                return PagoRead.model_validate(pago), None

            init_point = (
                response_data.get("sandbox_init_point")
                or response_data.get("init_point")
                or None
            )
            preference_id = response_data.get("id")

            # Note: MP preference IDs contain hyphens and cannot be stored in
            # mp_payment_id (int column). mp_payment_id is reserved for the
            # numeric payment ID received via the webhook.

            pago_read = PagoRead.model_validate(pago)
            return pago_read, init_point

        except Exception as exc:
            logger.exception("Error creating MP preference for pedido %s", pedido_id)
            return PagoRead.model_validate(pago), None

    @staticmethod
    def check_pedido_status(
        session: Session,
        external_reference: str,
        current_user,
    ) -> dict:
        """Polling endpoint: check if a Pedido has been created for this payment.

        Proactive fallback: if the Pago is still pending and the webhook
        hasn't fired (common in local dev without ngrok), this method
        fetches the real payment status from MP's API and creates the
        Pedido synchronously if the payment was approved.
        """
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            pago = uow.pagos.get_by_external_reference(external_reference)

            # Not found at all
            if pago is None:
                return {"status": "not_found", "pedido_id": None, "mp_status": None, "costo_envio": None}

            # Cross-user check: return not_found to avoid leaking information
            snapshot = uow.snapshots.get_by_external_reference(external_reference)
            owner_id = snapshot.usuario_id if snapshot else None

            # If snapshot exists and belongs to a different user -> deny
            if owner_id is not None and owner_id != current_user.id:
                return {"status": "not_found", "pedido_id": None, "mp_status": None, "costo_envio": None}

            # If snapshot was consumed (None) but pago has pedido_id, verify ownership via Pedido
            if snapshot is None and pago.pedido_id is not None:
                pedido = uow.pedidos.get_by_id(pago.pedido_id)
                if pedido is not None and pedido.usuario_id != current_user.id:
                    return {"status": "not_found", "pedido_id": None, "mp_status": None, "costo_envio": None}

            # Pedido already created -> found
            if pago.pedido_id is not None:
                pedido = uow.pedidos.get_by_id(pago.pedido_id)
                costo_envio_val = float(pedido.costo_envio) if (pedido is not None and pedido.costo_envio is not None) else 0.0
                return {
                    "status": "found",
                    "pedido_id": pago.pedido_id,
                    "mp_status": pago.mp_status,
                    "costo_envio": costo_envio_val,
                }

            # ── PROACTIVE FALLBACK: check MP API for real payment status ──
            # In local dev without ngrok, the webhook never fires. This fallback
            # searches MercadoPago's API by external_reference to find the payment,
            # then creates the Pedido synchronously if the payment was approved.
            # Only activates after 8 seconds to avoid hitting MP's API too early.
            if pago.mp_status == "pending" and pago.pedido_id is None:
                from datetime import datetime as _dt, timezone as _tz
                age_seconds = (_dt.now(_tz.utc) - pago.created_at.replace(tzinfo=_tz.utc)).total_seconds()
                if age_seconds > 3:
                    # Try mp_payment_id first (set if webhook partially fired)
                    mp_pid = pago.mp_payment_id
                    payment_data = None
                    if mp_pid is not None:
                        payment_data = PagoService.get_payment_from_mp(mp_pid)
                    if payment_data is None:
                        # Fallback: search MP by external_reference
                        payment_data = PagoService._search_mp_payment(external_reference)
                    
                    if payment_data:
                        mp_status = payment_data.get("status", "unknown")
                        mp_pid_found = payment_data.get("id")
                        logger.info("[STATUS-POLL] MP API returned status=%s id=%s for ext_ref=%s", mp_status, mp_pid_found, external_reference[:16])
                        if mp_status == "approved":
                            try:
                                # ── Steps A+B+C in a SINGLE UoW (atomic) ──
                                with VentasPagosTrazabilidadUnitOfWork(session) as uow_proactive:
                                    # Step A: Update Pago status
                                    db_pago = uow_proactive.pagos.get_by_id(pago.id)
                                    if db_pago and db_pago.pedido_id is None:
                                        db_pago.mp_payment_id = mp_pid_found
                                        db_pago.mp_status = "approved"
                                        db_pago.mp_status_detail = payment_data.get("status_detail")
                                        db_pago.payment_method_id = payment_data.get("payment_method_id")
                                        mp_ta = payment_data.get("transaction_amount")
                                        if mp_ta is not None:
                                            db_pago.transaction_amount = float(mp_ta)
                                        uow_proactive.pagos.update(db_pago)

                                        # Step B: Create Pedido from snapshot (same UoW)
                                        if snapshot is not None:
                                            nuevo_pedido = PedidoService.crear_desde_snapshot(
                                                session, snapshot, uow=uow_proactive,
                                            )

                                            # Step C: Backfill pedido_id (same UoW, ORM)
                                            db_pago.pedido_id = nuevo_pedido.id
                                            uow_proactive.pagos.update(db_pago)

                                            # Save for post-commit broadcast
                                            _proactive_pedido_id = nuevo_pedido.id
                                            _proactive_usuario_id = nuevo_pedido.usuario_id
                                            _proactive_costo_envio = float(nuevo_pedido.costo_envio) if nuevo_pedido.costo_envio else 0.0
                                            _proactive_has_pedido = True
                                        else:
                                            _proactive_has_pedido = False

                                # ── AFTER UoW commit: broadcast ──
                                if _proactive_has_pedido:
                                    ws_manager = get_ws_manager()
                                    payload = {
                                        "event": "pago_confirmado",
                                        "pedido_id": _proactive_pedido_id,
                                        "estado_anterior": None,
                                        "estado_nuevo": "CONFIRMADO",
                                        "usuario_id": _proactive_usuario_id,
                                        "motivo": None,
                                        "timestamp": datetime.utcnow().isoformat(),
                                    }
                                    fire_broadcast(ws_manager, _proactive_pedido_id, payload)
                                    fire_broadcast_admin(ws_manager, payload)
                                    fire_broadcast_user(ws_manager, _proactive_usuario_id, payload)

                                    return {
                                        "status": "found",
                                        "pedido_id": _proactive_pedido_id,
                                        "mp_status": "approved",
                                        "costo_envio": _proactive_costo_envio,
                                    }
                                else:
                                    return {"status": "pending", "pedido_id": None, "mp_status": "approved", "costo_envio": None}
                            except Exception as e:
                                logger.exception(
                                    "check_pedido_status: proactive Pedido creation failed for ext_ref=%s: %s",
                                    external_reference, e,
                                )
                                # Return the actual error so the frontend can show it to the user
                                error_msg = str(getattr(e, 'detail', e))
                                return {"status": "error", "pedido_id": None, "mp_status": mp_status, "costo_envio": None, "error": error_msg}

            # Pago approved but Pedido was never created (snapshot gone).
            # Surface a clear error instead of an endless "pending" spinner.
            if pago.mp_status == "approved" and pago.pedido_id is None:
                logger.warning(
                    "check_pedido_status: Pago id=%s approved but pedido_id is None "
                    "and snapshot is gone (external_reference=%s). Cannot create Pedido.",
                    pago.id, external_reference[:16],
                )
                return {
                    "status": "error",
                    "pedido_id": None,
                    "mp_status": pago.mp_status,
                    "error": "El pago fue aprobado pero no se pudo recuperar el carrito para crear el pedido. Contacta a soporte.",
                }

            # Otherwise: pago exists but not approved (e.g., still pending)
            return {"status": "not_found", "pedido_id": None, "mp_status": pago.mp_status, "costo_envio": None}

    @staticmethod
    def resolve_user_from_payment_ref(
        session: Session,
        external_reference: str,
    ):
        """Resolve the Usuario who owns the payment identified by external_reference.

        Used as an alternative auth mechanism for the post-pago redirect flow:
        the external_reference UUID travels through the MP redirect and acts
        as a temporary credential — only the user who initiated the payment
        knows this UUID.

        Primary path: lookup via CarritoSnapshot (still exists before webhook).
        Fallback path: lookup via Pago -> Pedido chain (snapshot consumed by webhook).

        Returns the Usuario if found, or None if the reference is invalid.
        """
        from app.modules.IdentidadYAcceso.uow import IdentidadYAccesoUnitOfWork

        # Primary path: lookup via CarritoSnapshot (still exists before webhook)
        vtas_uow = VentasPagosTrazabilidadUnitOfWork(session)
        snapshot = vtas_uow.snapshots.get_by_external_reference(external_reference)
        if snapshot is not None:
            identidad_uow = IdentidadYAccesoUnitOfWork(session)
            user = identidad_uow.usuarios.get_with_roles(snapshot.usuario_id)
            if user is not None:
                return user
            logger.warning(
                "resolve_user_from_payment_ref: snapshot found for external_reference=%s "
                "but user_id=%s not found in DB",
                external_reference[:16], snapshot.usuario_id,
            )
            return None

        # Fallback: snapshot was already consumed by webhook.
        # Resolve via Pago -> Pedido -> usuario_id chain.
        pago = vtas_uow.pagos.get_by_external_reference(external_reference)
        if pago is not None:
            if pago.pedido_id is not None:
                pedido = vtas_uow.pedidos.get_by_id(pago.pedido_id)
                if pedido is not None:
                    identidad_uow = IdentidadYAccesoUnitOfWork(session)
                    return identidad_uow.usuarios.get_with_roles(pedido.usuario_id)
            else:
                logger.warning(
                    "resolve_user_from_payment_ref: Pago found (id=%s) but pedido_id is "
                    "None (webhook not yet processed). Snapshot was %s.",
                    pago.id,
                    "found" if snapshot is not None else "NOT found",
                )
        else:
            logger.warning(
                "resolve_user_from_payment_ref: No Pago found for external_reference=%s",
                external_reference[:16],
            )

        # Also handle: Pago exists but pedido not yet created (webhook still pending)
        # and snapshot was deleted by expiration (TTL). In this case we still know
        # the user from the Pago's preference context, but we have no user ID stored
        # directly on Pago. This is an edge case that should be rare — return None.
        return None

    @staticmethod
    def update_pago_status(
        session: Session,
        mp_payment_id: int,
        mp_status: str,
        mp_status_detail: str | None = None,
    ) -> PagoRead:
        """Update a Pago record's status from a MercadoPago webhook callback."""
        with VentasPagosTrazabilidadUnitOfWork(session) as uow:
            pago = uow.pagos.get_by_mp_payment_id(mp_payment_id)
            if not pago:
                raise ValueError(f"Pago con MP ID {mp_payment_id} no encontrado")

            pago.mp_status = mp_status
            pago.mp_status_detail = mp_status_detail
            pago.mp_payment_id = mp_payment_id
            uow.pagos.update(pago)
            return PagoRead.model_validate(pago)

    @staticmethod
    def get_pagos_by_pedido(session: Session, pedido_id: int) -> List[PagoRead]:
        """List all payments for an order, newest first."""
        repo = PagoRepository(session)
        pagos = repo.get_by_pedido(pedido_id)
        return [PagoRead.model_validate(p) for p in pagos]

    @staticmethod
    def get_pagos_by_pedido_autorizado(
        session: Session,
        pedido_id: int,
        current_user,
    ) -> List[PagoRead]:
        """List payments for a pedido with authorization checks.

        Orchestrates across PedidoService (for ownership validation) and
        PagoService (for payment listing). This is the single entry point
        called by the Pago router — the router never calls PedidoService
        directly.

        Admins and PEDIDOS-role users can view any pedido's payments.
        Regular users can only view their own pedidos' payments.
        """
        pedido = PedidoService.get_by_id(session, pedido_id)
        get_or_404(pedido, "Pedido no encontrado")

        if not any(rol.codigo in ("ADMIN", "PEDIDOS") for rol in current_user.roles):
            if pedido.usuario_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para ver este pedido",
                )

        return PagoService.get_pagos_by_pedido(session, pedido_id)

    @staticmethod
    def process_webhook(body: dict, background_tasks=None) -> dict:
        """Process a MercadoPago IPN webhook notification.

        Flow:
        1. Extract mp_payment_id from the webhook payload
        2. Fetch REAL payment status from MP API (never trust webhook data)
        3. Deduplicate by idempotency_key
        4. Update Pago record
        5. If approved: look up cart_snapshot, create Pedido from snapshot,
           backfill pago.pedido_id, delete snapshot, broadcast pago_confirmado
        6. If rejected: just update Pago status (snapshot preserved for retry)

        POST-PAGO flow: The Pedido is CREATED here, not advanced from PENDIENTE.
        """
        import json as _json

        logger.info("MP webhook received: %s", _json.dumps(body, default=str))

        # ── Extract mp_payment_id ──
        mp_payment_id: int | None = None

        raw_id = body.get("id")
        if raw_id and body.get("topic") == "payment":
            mp_payment_id = int(raw_id)

        if mp_payment_id is None:
            topic = body.get("topic", "")
            action = body.get("action", "")
            if topic != "payment" and "payment" not in action:
                return {"status": "ignored", "detail": "not a payment notification"}

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

        # ── Fetch real status from MP API ──
        logger.info("[WEBHOOK] mp_payment_id=%s, fetching from MP API...", mp_payment_id)
        payment_data = PagoService.get_payment_from_mp(mp_payment_id)
        if not payment_data:
            logger.warning("[WEBHOOK] FAILED to fetch payment %s from MP API!", mp_payment_id)
            logger.warning(
                "MP webhook: could not fetch payment %s from MP API",
                mp_payment_id,
            )
            return {"status": "received", "detail": "could not fetch from MP"}

        mp_status = payment_data.get("status", "unknown")
        logger.info("[WEBHOOK] payment_status=%s, ext_ref=%s...", mp_status, payment_data.get('external_reference', 'N/A')[:16])
        mp_status_detail = payment_data.get("status_detail")
        external_reference = payment_data.get("external_reference", "")
        idempotency_key = payment_data.get("idempotency_key", str(uuid.uuid4()))

        # ── Process in background to return 200 immediately ──
        from app.core.database import engine as _engine
        from sqlmodel import Session as _Session

        def _process():
            logger.info("[WEBHOOK-PROCESS] Starting background processing for ext_ref=%s...", external_reference[:16])
            with _Session(_engine) as _session:
                repo = PagoRepository(_session)

                # Deduplicate: check if already processed with this key (READ-ONLY, before UoW)
                existing = repo.get_by_idempotency_key(idempotency_key)
                if existing and existing.mp_status in ("approved", "rejected"):
                    logger.info(
                        "MP webhook: duplicate ignored for idempotency_key=%s, status=%s",
                        idempotency_key, existing.mp_status,
                    )
                    return

                # Find existing Pago by external_reference (READ-ONLY, before UoW)
                pago = repo.get_by_external_reference(external_reference)
                if not pago:
                    logger.warning("[WEBHOOK-PROCESS] No Pago found for ext_ref=%s", external_reference[:16])
                    logger.warning(
                        "MP webhook: no Pago found for external_reference=%s",
                        external_reference,
                    )
                    return
                logger.info("[WEBHOOK-PROCESS] Found Pago id=%s, mp_status=%s, pedido_id=%s", pago.id, pago.mp_status, pago.pedido_id)

                # ── Steps A+B+C in a SINGLE UoW (atomic) ──
                # If any step fails, the UoW __exit__ rolls back everything.
                # No manual compensation needed.
                _should_broadcast = False
                _broadcast_pedido_id = None
                _broadcast_pedido_usuario_id = None

                try:
                    with VentasPagosTrazabilidadUnitOfWork(_session) as uow:
                        # Step A: Update Pago status
                        db_pago = uow.pagos.get_by_id(pago.id)
                        if not db_pago:
                            logger.warning("MP webhook: Pago %s not found in UoW", pago.id)
                            return

                        db_pago.mp_payment_id = mp_payment_id
                        db_pago.mp_status = mp_status
                        db_pago.mp_status_detail = mp_status_detail
                        db_pago.payment_method_id = payment_data.get("payment_method_id")
                        mp_transaction_amount = payment_data.get("transaction_amount")
                        if mp_transaction_amount is not None:
                            db_pago.transaction_amount = float(mp_transaction_amount)
                        uow.pagos.update(db_pago)

                        if mp_status == "approved":
                            snapshot = uow.snapshots.get_by_external_reference(external_reference)
                            if snapshot is not None:
                                # Step B: Create Pedido from snapshot (same UoW)
                                nuevo_pedido = PedidoService.crear_desde_snapshot(
                                    _session, snapshot, uow=uow,
                                )

                                # Step C: Backfill pedido_id (same UoW, ORM)
                                db_pago.pedido_id = nuevo_pedido.id
                                uow.pagos.update(db_pago)

                                _should_broadcast = True
                                _broadcast_pedido_id = nuevo_pedido.id
                                _broadcast_pedido_usuario_id = nuevo_pedido.usuario_id
                                logger.info("[WEBHOOK-PROCESS] Pedido creado id=%s", nuevo_pedido.id)
                            else:
                                logger.warning("[WEBHOOK-PROCESS] Snapshot ALREADY consumed for ext_ref=%s", external_reference[:16])
                        # UoW commits here if no exception — all steps atomic

                except Exception as e:
                    logger.exception(
                        "MP webhook: error processing payment for ext_ref=%s: %s",
                        external_reference, e,
                    )
                    # UoW __exit__ automatically rolled back Pago status update.
                    # No manual compensation needed — Pago remains in pre-webhook state.
                    logger.warning("[WEBHOOK-PROCESS] Processing FAILED: %s. UoW rolled back ALL changes.", e)
                    return

                # ── AFTER UoW commit: broadcast ──
                if _should_broadcast:
                    ws_manager = get_ws_manager()
                    payload = {
                        "event": "pago_confirmado",
                        "pedido_id": _broadcast_pedido_id,
                        "estado_anterior": None,
                        "estado_nuevo": "CONFIRMADO",
                        "usuario_id": _broadcast_pedido_usuario_id,
                        "motivo": None,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    fire_broadcast(ws_manager, _broadcast_pedido_id, payload)
                    fire_broadcast_admin(ws_manager, payload)
                    fire_broadcast_user(ws_manager, _broadcast_pedido_usuario_id, payload)

                logger.info(
                    "MP webhook: payment %s processed, status=%s",
                    mp_payment_id, mp_status,
                )

        if background_tasks is not None:
            background_tasks.add_task(_process)
        else:
            _process()

        return {"status": "received", "detail": "ok"}

    @staticmethod
    def get_payment_from_mp(mp_payment_id: int) -> dict | None:
        """Fetch payment details from MercadoPago API by MP payment ID."""
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

    @staticmethod
    def _search_mp_payment(external_reference: str) -> dict | None:
        """Search MercadoPago for a payment by external_reference.

        Used as a fallback when the webhook doesn't fire (e.g., local dev
        without ngrok). Returns the first matching payment or None.
        """
        try:
            sdk = _get_mp_sdk()
            response = sdk.payment().search({"external_reference": external_reference})
            results = response.get("response", {}).get("results", [])
            if results:
                return results[0]
            return None
        except Exception as exc:
            logger.exception("Error searching MP payments for ext_ref=%s", external_reference[:16])
            return None
