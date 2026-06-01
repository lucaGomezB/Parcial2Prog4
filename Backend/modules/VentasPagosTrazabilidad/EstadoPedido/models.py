"""
EstadoPedido models — Order status catalog table.

This is a CATALOG table (like an enum in the database), not transactional data.
It defines the possible states an order can be in.

SEMANTIC PRIMARY KEY:
    Uses a string 'codigo' instead of an auto-increment integer.
    This makes the code self-documenting:
        estado_codigo = "PENDIENTE"
        if estado_codigo in ESTADOS_TERMINALES: ...

Typical seed data:
    PENDIENTE  | Pendiente             | 1 | false
    CONFIRMADO | Confirmado            | 2 | false
    EN_PREP    | En preparacion        | 3 | false
    EN_CAMINO  | En camino             | 4 | false
    ENTREGADO  | Entregado             | 5 | true
    CANCELADO  | Cancelado             | 6 | true
"""
from typing import Optional
from sqlmodel import Field
from models.base import TimestampModel


class EstadoPedido(TimestampModel, table=True):
    """Order status catalog table (estadopedido)."""

    __tablename__ = "estadopedido"

    codigo: str = Field(primary_key=True, max_length=20)
    descripcion: str = Field(max_length=80, nullable=False)
    orden: int = Field(nullable=False)
    es_terminal: bool = Field(nullable=False)
