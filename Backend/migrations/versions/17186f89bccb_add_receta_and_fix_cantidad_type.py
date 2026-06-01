"""Add receta (recipe) field to producto and fix cantidad type in productoingrediente.

Changes:
  1. Adds a receta column (text field, up to 5000 chars) to the producto table
     for storing preparation instructions or recipe notes.
  2. Changes the cantidad column in productoingrediente from VARCHAR(50) back
     to Integer, with a USING clause to safely cast existing string values.

Revision ID: 17186f89bccb
Revises: ffd0e326879c
Create Date: 2026-05-31 18:10:44.239693
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17186f89bccb'
down_revision: Union[str, Sequence[str], None] = 'ffd0e326879c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply migration: add recipe field and convert cantidad to Integer.

    The USING clause handles existing data by rounding the string-cast-as-numeric
    value to the nearest integer, preventing data loss during the type change.
    """
    # Add a free-text recipe/instructions field to each product.
    op.add_column('producto', sa.Column('receta', sa.String(length=5000), nullable=True))
    # Change cantidad from VARCHAR to Integer.
    # ROUND(CAST(cantidad AS numeric))::integer safely converts existing string
    # values like '1.5' or '2' to integers without breaking the migration.
    op.alter_column('productoingrediente', 'cantidad',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.Integer(),
               postgresql_using='ROUND(CAST(cantidad AS numeric))::integer',
               existing_nullable=False)


def downgrade() -> None:
    """Revert: convert cantidad back to VARCHAR and drop the recipe column."""
    op.alter_column('productoingrediente', 'cantidad',
               existing_type=sa.Integer(),
               type_=sa.VARCHAR(length=50),
               existing_nullable=True)
    op.drop_column('producto', 'receta')
