"""Add factor_conversion column to unidadmedida table.

Adds a Decimal column factor_conversion that stores how many base units
equal one of this measurement unit. Base units have factor=1.

Revision ID: add_factor_conversion_unidadmedida
Revises: fix_fsm_es_sistema
Create Date: 2026-06-29

Factors seeded:
    kilogramo(1)  → 1000  (1000g = 1kg)
    gramo(2)      → 1     (base)
    litro(3)      → 1000  (1000mL = 1L)
    mililitro(4)  → 1     (base)
    pieza(5)      → 1     (base)
    docena(6)     → 12    (12p = 1doc)
    m²(7)         → 1     (base)
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from decimal import Decimal


revision: str = "add_factor_conv_unidadmedida"
down_revision: Union[str, None] = "3c6f4436ffc9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "unidadmedida",
        sa.Column(
            "factor_conversion",
            sa.Numeric(precision=10, scale=3),
            nullable=False,
            server_default="1",
        ),
    )
    # Update existing rows with correct conversion factors
    factores = {
        1: Decimal("1000"),   # kg → g
        2: Decimal("1"),       # g (base)
        3: Decimal("1000"),   # L → mL
        4: Decimal("1"),       # mL (base)
        5: Decimal("1"),       # pieza (base)
        6: Decimal("12"),     # docena → pieza
        7: Decimal("1"),       # m² (base)
    }
    for uid, factor in factores.items():
        op.execute(
            sa.text(
                "UPDATE unidadmedida SET factor_conversion = :factor WHERE id = :uid"
            ).bindparams(factor=factor, uid=uid)
        )


def downgrade() -> None:
    op.drop_column("unidadmedida", "factor_conversion")
