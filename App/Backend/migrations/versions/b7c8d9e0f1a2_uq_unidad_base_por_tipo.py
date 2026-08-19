"""Add partial unique index to prevent duplicate base units per tipo.

Creates a partial unique index on unidadmedida(tipo) WHERE factor_conversion = 1.
This ensures at most one base unit exists per measurement type at the database level.

Revision ID: b7c8d9e0f1a2
Revises: 2efe9c640b22
Create Date: 2026-07-27
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, None] = "2efe9c640b22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create partial unique index on unidadmedida(tipo) WHERE factor_conversion = 1."""
    op.create_index(
        "uq_unidad_base_por_tipo",
        "unidadmedida",
        ["tipo"],
        unique=True,
        postgresql_where=text("factor_conversion = 1"),
    )


def downgrade() -> None:
    """Remove the partial unique index."""
    op.drop_index(
        "uq_unidad_base_por_tipo",
        table_name="unidadmedida",
        postgresql_where=text("factor_conversion = 1"),
    )
