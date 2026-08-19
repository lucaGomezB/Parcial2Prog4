"""Add direccion_snapshot (JSON) column to pedido table.

Stores a snapshot of the delivery address at order creation time:
  { "linea1": "...", "linea2": "...", "ciudad": "..." }

This guarantees historical accuracy — if the address is later modified
or soft-deleted, the order still retains the address data as it was
when the order was placed. Mirrors the same snapshot pattern already
used for nombre_snapshot / precio_snapshot in DetallePedido.

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-06-11
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '5e6f7a8b9c0d'
down_revision: Union[str, None] = '4d5e6f7a8b9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add direccion_snapshot JSON column to pedido table."""
    op.add_column('pedido', sa.Column('direccion_snapshot', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove direccion_snapshot column from pedido table."""
    op.drop_column('pedido', 'direccion_snapshot')
