"""
Shared utilities for the CatalogoDeProductos module.

Unit conversion functions extracted from Producto/service.py so they can
be reused by ProductoRepository for derived stock computation without
creating a circular dependency.
"""
from decimal import Decimal

from sqlmodel import select

from .UnidadMedida.models import UnidadMedida


# ── Unit conversion factors ──────────────────────────────────────────────
# Each UnidadMedida ID maps to its conversion factor relative to the
# canonical base unit of its tipo (gramo for masa, mililitro for volumen,
# porcion for unidad, metro cuadrado for area).
#
# Base units (factor=1): g(2), mL(4), porcion(5), m²(7)
# These are also stored in the unidadmedida.factor_conversion column.
# The dict below is the canonical seed; _load_conversion_factors()
# reads from the DB at runtime.
_CONVERSION: dict[int, Decimal] = {
    1: Decimal("1000"),   # kg → g
    2: Decimal("1"),       # g (base)
    3: Decimal("1000"),   # L → mL
    4: Decimal("1"),       # mL (base)
    5: Decimal("1"),       # porcion (base)
    6: Decimal("12"),     # docena → porcion
    7: Decimal("1"),       # m² (base)
}


def load_conversion_factors(session) -> dict[int, Decimal]:
    """Load conversion factors from the UnidadMedida table.

    Falls back to the hardcoded _CONVERSION dict if the table is empty
    (e.g. during tests before seeding).
    """
    rows = session.exec(select(UnidadMedida.id, UnidadMedida.factor_conversion)).all()
    if not rows:
        return dict(_CONVERSION)
    return {row[0]: Decimal(str(row[1])) for row in rows}


def convertir_cantidad(
    cantidad: Decimal,
    unidad_origen_id: int | None,
    unidad_destino_id: int | None,
    factores: dict[int, Decimal] | None = None,
) -> Decimal:
    """Convert a quantity from one unit to another within the same tipo.

    When both units are the same or either is None, returns cantidad unchanged.
    Uses conversion factors relative to each tipo's base unit.
    If factores is not provided, falls back to the hardcoded _CONVERSION dict.

    The caller is expected to apply int() or math.floor() to the result.
    Since all values are positive, int(Decimal) and math.floor() produce
    identical results.
    """
    if unidad_origen_id is None or unidad_destino_id is None:
        return cantidad
    if unidad_origen_id == unidad_destino_id:
        return cantidad
    if factores is None:
        factores = _CONVERSION
    factor_origen = factores.get(unidad_origen_id, Decimal("1"))
    factor_destino = factores.get(unidad_destino_id, Decimal("1"))
    return cantidad * (factor_origen / factor_destino)
