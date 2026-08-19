"""Change cantidad column from Integer to Numeric(10,3) with CHECK > 0.

Rationale: Product recipes need fractional ingredient quantities (0.500 kg, 1.250 L).
Integer cannot express fractions. Decimal(10,3) provides precision for up to 3 decimal
places with safe arithmetic for price calculation.

Revision ID: 19f7b093aee3
Revises: e80e87086762
Create Date: 2026-06-21 16:03:47.809541
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19f7b093aee3'
down_revision: Union[str, Sequence[str], None] = 'e80e87086762'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change cantidad from Integer to Numeric(10,3) and add CHECK > 0.

    Existing integer values (1, 2, etc.) are safely cast to numeric
    via the USING clause. Then a CHECK constraint is added to reject
    zero or negative values at the database level.
    """
    # Task 1.1: Alter column type to NUMERIC(10,3)
    op.execute(
        "ALTER TABLE productoingrediente "
        "ALTER COLUMN cantidad TYPE NUMERIC(10,3) "
        "USING cantidad::numeric(10,3)"
    )
    # Task 1.2: Add CHECK constraint cantidad > 0
    op.create_check_constraint(
        "ck_pi_cantidad_positive",
        "productoingrediente",
        "cantidad > 0"
    )


def downgrade() -> None:
    """Revert: drop CHECK constraint and cast cantidad back to Integer.

    Fractional values (e.g., 0.500) are truncated to integers.
    If any non-numeric values existed before this migration, the
    downgrade will fail — this is expected and intentional.
    """
    # Task 1.3: Drop CHECK constraint then cast back to Integer
    op.drop_constraint("ck_pi_cantidad_positive", "productoingrediente")
    op.execute(
        "ALTER TABLE productoingrediente "
        "ALTER COLUMN cantidad TYPE INTEGER "
        "USING cantidad::integer"
    )
