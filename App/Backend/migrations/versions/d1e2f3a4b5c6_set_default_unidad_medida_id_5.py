"""Set default unidad_medida_id to 5 (Porcion) for existing products.

Updates all product rows where unidad_medida_id IS NULL to use ID 5 (Porcion)
as the default measurement unit. This complements the application-level default
in ProductoService.create() for new products.

Revision ID: d1e2f3a4b5c6
Revises: c0b11cb4bbea
Create Date: 2026-08-03
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c0b11cb4bbea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set unidad_medida_id = 5 for all products where it is NULL."""
    op.execute("UPDATE producto SET unidad_medida_id = 5 WHERE unidad_medida_id IS NULL")


def downgrade() -> None:
    """No meaningful downgrade — reverting would lose data semantics."""
    pass
