"""Rename es_insumo to es_producto_terminado in producto table.

The field was semantically misnamed. es_insumo meant "this product is a
finished good bought and resold as-is (no recipe tracking, manual pricing)"
but insumo in Spanish means "input/raw material". Renaming to
es_producto_terminado (finished product) fixes the semantic mismatch.

This is a metadata-only PostgreSQL RENAME COLUMN operation (O(1), no table
rewrite). Boolean values remain unchanged.

Revision ID: r1a2b3c4d5e6
Revises: b7c8d9e0f1a2
Create Date: 2026-07-29

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'r1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename es_insumo column to es_producto_terminado."""
    op.execute(
        "ALTER TABLE producto RENAME COLUMN es_insumo TO es_producto_terminado"
    )


def downgrade() -> None:
    """Reverse rename: es_producto_terminado back to es_insumo."""
    op.execute(
        "ALTER TABLE producto RENAME COLUMN es_producto_terminado TO es_insumo"
    )
