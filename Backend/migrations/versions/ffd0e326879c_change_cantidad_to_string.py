"""Change cantidad column type from Numeric to String.

Rationale: The cantidad (quantity) field in productoingrediente originally stored
decimal values, but the domain evolved to accept non-numeric quantity descriptions
(e.g. "al gusto", "1 unidad", "50g"). Changing the column to VARCHAR(50) allows
free-form text while preserving existing numeric values as strings.

Revision ID: ffd0e326879c
Revises: 1859de7b45ad
Create Date: 2026-05-31 17:54:31.673688
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ffd0e326879c'
down_revision: Union[str, Sequence[str], None] = '1859de7b45ad'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change cantidad from Numeric(10,2) to String(50).

    Existing numeric values are implicitly cast to their string representation
    by PostgreSQL during the ALTER COLUMN operation.
    """
    op.alter_column('productoingrediente', 'cantidad',
               existing_type=sa.NUMERIC(precision=10, scale=2),
               type_=sa.String(length=50),
               existing_nullable=False)


def downgrade() -> None:
    """Revert cantidad back to Numeric(10,2).

    WARNING: If any non-numeric strings were stored in the column, this
    downgrade will fail with a type-cast error.
    """
    op.alter_column('productoingrediente', 'cantidad',
               existing_type=sa.String(length=50),
               type_=sa.NUMERIC(precision=10, scale=2),
               existing_nullable=False)
