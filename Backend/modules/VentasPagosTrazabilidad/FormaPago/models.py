"""
FormaPago models — Payment method catalog table.

Like EstadoPedido, uses a SEMANTIC PRIMARY KEY (string 'codigo')
instead of an auto-increment ID, making it self-documenting:
    forma_pago_codigo = "MP"  # MercadoPago

The 'habilitado' flag allows disabling a payment method without
removing it (existing orders still reference the code).

Typical seed data:
    EFECTIVO | Efectivo        | true
    MP       | Mercado Pago    | true
    TARJETA  | Tarjeta         | true
"""
from typing import Optional
from sqlmodel import Field
from models.base import TimestampModel


class FormaPago(TimestampModel, table=True):
    """Payment method catalog table (formapago)."""

    __tablename__ = "formapago"

    codigo: str = Field(primary_key=True, max_length=20)
    descripcion: str = Field(max_length=80, nullable=False)
    habilitado: bool = Field(default=True, nullable=False)
