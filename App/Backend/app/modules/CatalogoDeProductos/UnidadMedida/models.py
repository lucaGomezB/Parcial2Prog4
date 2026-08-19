"""
UnidadMedida model — Immutable measurement unit catalog entity.

Design decisions (from design.md):
    - Surrogate BIGSERIAL PK (not semantic; both nombre and simbolo are UNIQUE)
    - No updated_at, no deleted_at (immutable catalog — D4)
    - tipo is VARCHAR(20) with application-level Literal validation (D3)
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import CheckConstraint, Column, Numeric


def _utcnow():
    """Return current UTC datetime, timezone-aware."""
    return datetime.now(timezone.utc)


if TYPE_CHECKING:
    from ..Producto.models import Producto
    from ..producto_ingrediente import ProductoIngrediente


class UnidadMedida(SQLModel, table=True):
    """Measurement unit catalog table.

    Columns:
        id: BIGSERIAL surrogate primary key
        nombre: human-readable unit name (UNIQUE, e.g. "kilogramo")
        simbolo: short symbol (UNIQUE, e.g. "kg")
        tipo: classification — masa, volumen, unidad, area
        factor_conversion: how many base units equal one of this unit.
            Base units (factor=1): gramo(2), mililitro(4), pieza(5), m²(7).
            Example: kilogramo → 1000 (1000g = 1kg), docena → 12 (12p = 1doc).
        created_at: record creation timestamp (UTC)
    """

    __tablename__ = "unidadmedida"

    __table_args__ = (
        CheckConstraint(
            "factor_conversion > 0",
            name="ck_unidadmedida_factor_positivo",
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True, sa_column_kwargs={"autoincrement": True})
    nombre: str = Field(max_length=50, nullable=False, unique=True)
    simbolo: str = Field(max_length=10, nullable=False, unique=True)
    tipo: str = Field(max_length=20, nullable=False)
    factor_conversion: Decimal = Field(default=Decimal("1"), sa_column=Column(Numeric(precision=10, scale=3), nullable=False))
    created_at: datetime = Field(default_factory=_utcnow, nullable=False)

    productos: List["Producto"] = Relationship(back_populates="unidad_medida")
    producto_ingredientes: List["ProductoIngrediente"] = Relationship(back_populates="unidad_medida")
    # ingredientes: one-way from Ingrediente side only (avoids circular import)
