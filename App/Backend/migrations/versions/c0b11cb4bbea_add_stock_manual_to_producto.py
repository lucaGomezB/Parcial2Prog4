"""add_stock_manual_to_producto

Adds stock_manual column to producto table for make-to-order migration.
es_producto_terminado=True products use stock_manual for inventory
instead of the deprecated stock_cantidad column (which now holds
derived stock computed from ingredient availability).

Revision ID: c0b11cb4bbea
Revises: r1a2b3c4d5e6
Create Date: 2026-07-30 17:49:26.731551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0b11cb4bbea'
down_revision: Union[str, Sequence[str], None] = 'r1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('producto', sa.Column('stock_manual', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('producto', 'stock_manual')
