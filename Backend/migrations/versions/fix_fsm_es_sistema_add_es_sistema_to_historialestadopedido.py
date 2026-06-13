"""Add es_sistema column to historialestadopedido table.

Adds a boolean column es_sistema to distinguish between user-triggered
state transitions and system-triggered ones (e.g., payment webhook).

When es_sistema=True, the transition was performed by the system/backend
automatically (no user involved). When False (default), it was an explicit
user action.

Revision ID: fix_fsm_es_sistema
Revises: 5e6f7a8b9c0d
Create Date: 2026-06-11

NOTE: The original design specified down_revision='fix_pedido_direccion_snapshot'
but that revision ID was never created. The actual head is 5e6f7a8b9c0d
(add_direccion_snapshot_to_pedido).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'fix_fsm_es_sistema'
down_revision: Union[str, Sequence[str], None] = '5e6f7a8b9c0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add es_sistema boolean column to historialestadopedido.

    Default FALSE ensures existing rows are treated as user-triggered.
    Server default is used to backfill existing rows.
    """
    op.add_column(
        'historialestadopedido',
        sa.Column('es_sistema', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )


def downgrade() -> None:
    """Remove es_sistema column from historialestadopedido.

    WARNING: Any data stored in es_sistema will be lost on downgrade.
    """
    op.drop_column('historialestadopedido', 'es_sistema')
