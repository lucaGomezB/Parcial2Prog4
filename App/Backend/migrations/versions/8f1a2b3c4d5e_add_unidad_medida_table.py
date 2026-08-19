"""Add unidadmedida table and unidad_medida_id FK columns.

Creates the unidadmedida lookup table for measurement units and adds
nullable unidad_medida_id foreign key columns to producto and
productoingrediente tables.

Table schema:
    - id: BIGSERIAL PRIMARY KEY
    - nombre: VARCHAR(50) UNIQUE NOT NULL
    - simbolo: VARCHAR(10) UNIQUE NOT NULL
    - tipo: VARCHAR(20) NOT NULL
    - created_at: TIMESTAMP NOT NULL (no updated_at, no deleted_at)

FK columns are nullable so existing data is unaffected.

Revision ID: 8f1a2b3c4d5e
Revises: 745f51d7c273
Create Date: 2026-06-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f1a2b3c4d5e'
down_revision: Union[str, Sequence[str], None] = '745f51d7c273'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create unidadmedida table and add FK columns to producto and productoingrediente."""
    op.create_table(
        'unidadmedida',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.String(length=50), nullable=False),
        sa.Column('simbolo', sa.String(length=10), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nombre'),
        sa.UniqueConstraint('simbolo'),
    )

    op.add_column(
        'producto',
        sa.Column('unidad_medida_id', sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        'fk_producto_unidad_medida_id',
        'producto', 'unidadmedida',
        ['unidad_medida_id'], ['id'],
    )

    op.add_column(
        'productoingrediente',
        sa.Column('unidad_medida_id', sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        'fk_productoingrediente_unidad_medida_id',
        'productoingrediente', 'unidadmedida',
        ['unidad_medida_id'], ['id'],
    )


def downgrade() -> None:
    """Remove FK columns from productoingrediente and producto, then drop unidadmedida table."""
    op.drop_constraint(
        'fk_productoingrediente_unidad_medida_id',
        'productoingrediente', type_='foreignkey',
    )
    op.drop_column('productoingrediente', 'unidad_medida_id')

    op.drop_constraint(
        'fk_producto_unidad_medida_id',
        'producto', type_='foreignkey',
    )
    op.drop_column('producto', 'unidad_medida_id')

    op.drop_table('unidadmedida')
