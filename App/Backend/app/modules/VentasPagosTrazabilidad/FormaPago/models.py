"""
FormaPago models — Payment method catalog table.

Like EstadoPedido, uses a SEMANTIC PRIMARY KEY (string 'codigo')
instead of an auto-increment ID, making it self-documenting:
    forma_pago_codigo = "MERCADOPAGO"  # MercadoPago

The 'habilitado' flag allows disabling a payment method without
removing it (existing orders still reference the code).

Current seed data:
    MERCADOPAGO   | MercadoPago                | true
    EFECTIVO      | Efectivo                   | true
    PAGO_LOCAL    | Pago y retiro en local      | true
    TRANSFERENCIA | Transferencia              | true
"""
from typing import Optional
from sqlmodel import Field
from app.core.base import TimestampModel


class FormaPago(TimestampModel, table=True):
    """Payment method catalog table (formapago)."""

    __tablename__ = "formapago"

    codigo: str = Field(primary_key=True, max_length=20)
    descripcion: str = Field(max_length=80, nullable=False)
    habilitado: bool = Field(default=True, nullable=False)
