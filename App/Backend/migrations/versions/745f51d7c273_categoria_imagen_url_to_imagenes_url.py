"""categoria_imagen_url_to_imagenes_url

Migrates Categoria.imagen_url (single optional string) to
Categoria.imagenes_url (JSON array of strings), preserving
existing image URLs.

Revision ID: 745f51d7c273
Revises: fix_fsm_es_sistema
Create Date: 2026-06-14 23:17:09.042494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '745f51d7c273'
down_revision: Union[str, Sequence[str], None] = 'fix_fsm_es_sistema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: add imagenes_url JSON column, migrate data, drop imagen_url."""
    # 1. Add the new JSON column with default empty array
    op.add_column(
        'categoria',
        sa.Column('imagenes_url', sa.JSON(), nullable=False, server_default=sa.text("'[]'::json"))
    )

    # 2. Migrate existing imagen_url values to single-element JSON arrays
    op.execute("""
        UPDATE categoria
        SET imagenes_url = CASE
            WHEN imagen_url IS NOT NULL THEN jsonb_build_array(imagen_url)
            ELSE '[]'::json
        END
    """)

    # 3. Drop the old column
    op.drop_column('categoria', 'imagen_url')


def downgrade() -> None:
    """Downgrade schema: add imagen_url back, migrate first element, drop imagenes_url."""
    # 1. Add the old column back
    op.add_column(
        'categoria',
        sa.Column('imagen_url', sa.VARCHAR(), autoincrement=False, nullable=True)
    )

    # 2. Migrate first element of imagenes_url back to imagen_url
    op.execute("""
        UPDATE categoria
        SET imagen_url = CASE
            WHEN jsonb_array_length(imagenes_url) > 0 THEN imagenes_url->>0
            ELSE NULL
        END
    """)

    # 3. Drop the new column
    op.drop_column('categoria', 'imagenes_url')
