"""Create carrito_snapshot table and make pago.pedido_id nullable.

Creates the carrito_snapshot table for persisting cart state during async
payment windows (MercadoPago redirect flow). The snapshot is created at
payment initiation and consumed (deleted) when the webhook confirms payment.

Also ALTERs pago.pedido_id from NOT NULL to nullable, since Pagos are now
created BEFORE Pedidos (the Pedido is created by the webhook on confirmation).

Revision ID: a1b2c3d4e5f6
Revises: ffd0e326879c
Create Date: 2026-06-16 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "ffd0e326879c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create carrito_snapshot table and make pago.pedido_id nullable."""

    # 1. ALTER pago.pedido_id to nullable (Pago is created before Pedido)
    op.alter_column(
        "pago",
        "pedido_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # 2. Create carrito_snapshot table
    op.create_table(
        "carrito_snapshot",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("direccion_id", sa.Integer(), nullable=True),
        sa.Column("direccion_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("forma_pago_codigo", sa.String(length=30), nullable=False),
        sa.Column("costo_envio", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "external_reference",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            columns=["usuario_id"],
            refcolumns=["usuario.id"],
            name="fk_carrito_snapshot_usuario_id",
        ),
        sa.ForeignKeyConstraint(
            columns=["direccion_id"],
            refcolumns=["direcciones_entrega.id"],
            name="fk_carrito_snapshot_direccion_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_carrito_snapshot"),
        sa.UniqueConstraint(
            "external_reference",
            name="uq_carrito_snapshot_external_reference",
        ),
    )

    # 3. Add indexes for performance
    op.create_index(
        "ix_carrito_snapshot_external_reference",
        "carrito_snapshot",
        ["external_reference"],
        unique=True,
    )
    op.create_index(
        "ix_carrito_snapshot_expires_at",
        "carrito_snapshot",
        ["expires_at"],
    )


def downgrade() -> None:
    """Drop carrito_snapshot table and restore pago.pedido_id NOT NULL."""

    # 1. Drop indexes
    op.drop_index(
        "ix_carrito_snapshot_expires_at",
        table_name="carrito_snapshot",
    )
    op.drop_index(
        "ix_carrito_snapshot_external_reference",
        table_name="carrito_snapshot",
    )

    # 2. Drop carrito_snapshot table
    op.drop_table("carrito_snapshot")

    # 3. Restore pago.pedido_id to NOT NULL (only safe if no NULL values exist)
    # In practice, unapplied pagos without pedido would need cleanup first.
    op.alter_column(
        "pago",
        "pedido_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
