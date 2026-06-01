"""Remove es_primordial from categoria and drop productomedida table.

Schema cleanup migration:
  - Drops the productomedida table (legacy product-variant model replaced by
    a different pricing/stock strategy).
  - Removes the es_primordial boolean column from categoria (concept no longer
    used in the domain model).
  - Retains the medida_snapshot field on related tables if present, as it
    stores historical data for order/invoice records.

Revision ID: 1859de7b45ad
Revises: a94d7efb265b
Create Date: 2026-05-30 19:20:10.162505
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1859de7b45ad'
down_revision: Union[str, Sequence[str], None] = 'a94d7efb265b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply cleanup: drop legacy table and column.

    productomedida stored product variants by size/measurement. The domain
    now handles variants differently, so this table is no longer needed.
    es_primordial was a boolean flag on categories that is no longer relevant.
    """
    # Drop the productomedida table entirely -- all FK-referencing data
    # in medida_snapshot (if any) is preserved for historical reporting.
    op.drop_table('productomedida')
    # Remove the es_primordial column from the categoria table.
    op.drop_column('categoria', 'es_primordial')
    # medida_snapshot is preserved in related tables for historical data.


def downgrade() -> None:
    """Revert cleanup: restore es_primordial column and productomedida table."""
    op.add_column('categoria', sa.Column('es_primordial', sa.BOOLEAN(), autoincrement=False, nullable=False))
    op.create_table('productomedida',
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('producto_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('nombre', sa.VARCHAR(length=100), autoincrement=False, nullable=False),
    sa.Column('precio', sa.NUMERIC(precision=10, scale=2), autoincrement=False, nullable=False),
    sa.Column('stock', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('orden', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('disponible', sa.BOOLEAN(), server_default=sa.text('true'), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['producto_id'], ['producto.id'], name=op.f('productomedida_producto_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('productomedida_pkey'))
    )
