"""Add es_insumo column to producto table.

Adds a boolean field es_insumo to the producto table, defaulting to FALSE.
This marks products that are resold items (not prepared by Food Store),
allowing them to be created without ingredients and with a manually set
base price.

All existing products default to es_insumo=False, making this a
backward-compatible additive migration.

Revision ID: 3a5b8c9d0e1f
Revises: 17186f89bccb
Create Date: 2026-06-04 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a5b8c9d0e1f'
down_revision: Union[str, Sequence[str], None] = '17186f89bccb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add es_insumo boolean column to producto, defaulting to FALSE.

    The server_default='0' ensures all existing rows get es_insumo=False
    without needing a data migration. The column is NOT NULL to maintain
    data integrity.
    """
    op.add_column(
        'producto',
        sa.Column(
            'es_insumo',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    """Remove the es_insumo column from producto.

    WARNING: Any data stored in es_insumo will be lost on downgrade.
    """
    op.drop_column('producto', 'es_insumo')
