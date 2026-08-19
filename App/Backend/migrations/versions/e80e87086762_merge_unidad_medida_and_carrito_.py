"""merge unidad-medida and carrito-snapshot branches

#Template para crear nuevas versiones automaticamente.

Revision ID: e80e87086762
Revises: 8f1a2b3c4d5e, a1b2c3d4e5f6
Create Date: 2026-06-16 20:08:56.717415

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e80e87086762'
down_revision: Union[str, Sequence[str], None] = ('8f1a2b3c4d5e', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
