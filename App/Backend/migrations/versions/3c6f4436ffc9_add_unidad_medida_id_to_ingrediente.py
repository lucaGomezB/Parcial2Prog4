"""add_unidad_medida_id_to_ingrediente

Adds optional unidad_medida_id FK to the ingrediente table so that
ingredient prices have a unit context (e.g., $8.00 / kg).

Revision ID: 3c6f4436ffc9
Revises: 19f7b093aee3
Create Date: 2026-06-21 17:27:41.855160
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3c6f4436ffc9'
down_revision: Union[str, Sequence[str], None] = '19f7b093aee3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ingrediente', sa.Column('unidad_medida_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_ingrediente_unidad_medida_id',
        'ingrediente', 'unidadmedida',
        ['unidad_medida_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_ingrediente_unidad_medida_id', 'ingrediente', type_='foreignkey')
    op.drop_column('ingrediente', 'unidad_medida_id')
