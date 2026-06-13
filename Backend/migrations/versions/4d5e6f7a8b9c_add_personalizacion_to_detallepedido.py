"""Add personalizacion column to detallepedido table.

Adds an ARRAY(Integer) column to store ingredient exclusion choices
for each order detail line. This enables customers to customize their
orders by removing specific ingredients from a product.

The column is nullable because existing orders predating this feature
have no personalization data.

Revision ID: 4d5e6f7a8b9c
Revises: 2a3b4c5d6e7f
Create Date: 2026-06-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4d5e6f7a8b9c'
down_revision: Union[str, Sequence[str], None] = '2a3b4c5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add personalizacion ARRAY(Integer) column to detallepedido.

    Uses postgresql.ARRAY for proper PostgreSQL array column support.
    The column is nullable to accommodate existing rows that were created
    before this feature existed.
    """
    op.add_column(
        'detallepedido',
        sa.Column('personalizacion', postgresql.ARRAY(sa.Integer()), nullable=True),
    )


def downgrade() -> None:
    """Remove the personalizacion column from detallepedido.

    WARNING: Any existing personalization data will be lost on downgrade.
    """
    op.drop_column('detallepedido', 'personalizacion')
