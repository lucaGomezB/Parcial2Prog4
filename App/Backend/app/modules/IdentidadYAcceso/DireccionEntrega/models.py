"""
DireccionEntrega (Delivery Address) domain model module.

Defines the SQLModel table for user delivery addresses with support for
geolocation (lat/long), multiple addresses per user, and a "principal"
(default) address flag.

Supports soft-delete to preserve historical order references.
"""

from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, Relationship, Column
from sqlalchemy import Numeric, Boolean
from app.core.base import TimestampModel, SoftDeleteModel

if TYPE_CHECKING:
    from ..Usuario.models import Usuario


class DireccionEntregaBase(TimestampModel):
    """
    Base class with shared delivery address fields.

    Fields include standard address components (line1, line2, city,
    province, postal code) plus optional geolocation coordinates
    (latitude/longitude) for mapping and delivery route optimization.

    es_principal: marks the default address for checkout pre-selection.
    Only one address per user can be principal at a time.
    """
    alias: Optional[str] = Field(default=None, max_length=50)
    linea1: str = Field(max_length=100, nullable=False)
    linea2: Optional[str] = Field(max_length=100)
    ciudad: str = Field(max_length=100, nullable=False)
    provincia: Optional[str] = Field(max_length=100)
    codigo_postal: Optional[str] = Field(max_length=10)
    latitud: Optional[Decimal] = Field(default=None, sa_type=Numeric(precision=9, scale=6))
    longitud: Optional[Decimal] = Field(default=None, sa_type=Numeric(precision=9, scale=6))
    es_principal: bool = Field(default=False)


class DireccionEntrega(DireccionEntregaBase, SoftDeleteModel, table=True):
    """
    Delivery address entity — stored in the 'direcciones_entrega' table.

    Each address belongs to a single user (N:1 relationship). When a user
    is deleted, their addresses are cascade-deleted (delete-orphan).

    Supports soft-delete: deleted addresses are hidden from queries but
    preserved for historical order references.
    """
    __tablename__: str = "direcciones_entrega"
    id: Optional[int] = Field(default=None, primary_key=True)

    # Flag: True means this is a company store/location (available for pickup) rather than a personal delivery address
    es_local: bool = Field(default=False, sa_column=Column(Boolean, default=False, nullable=False))

    # N:1 relationship: each address belongs to one user
    usuario_id: int = Field(foreign_key="usuario.id", nullable=False, ondelete="CASCADE")
    usuario: "Usuario" = Relationship(back_populates="direcciones_entrega")
