"""add_es_local_to_direccion_entrega

Add es_local boolean column to direcciones_entrega for company store/location flag.

Revision ID: 2efe9c640b22
Revises: add_factor_conv_unidadmedida
Create Date: 2026-07-06 17:55:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = '2efe9c640b22'
down_revision: Union[str, Sequence[str], None] = 'add_factor_conv_unidadmedida'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add es_local column (company store/location flag)."""
    op.execute(
        "ALTER TABLE direcciones_entrega "
        "ADD COLUMN IF NOT EXISTS es_local BOOLEAN NOT NULL DEFAULT false"
    )


def downgrade() -> None:
    """Remove es_local column."""
    op.execute("ALTER TABLE direcciones_entrega DROP COLUMN IF EXISTS es_local")
