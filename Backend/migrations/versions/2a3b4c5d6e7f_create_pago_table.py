"""Create pago (payment) table.

Creates the pago table for tracking payments associated with orders.
Supports MercadoPago integration fields and idempotency keys.

Revision ID: 2a3b4c5d6e7f
Revises: 448487941269
Create Date: 2026-06-10 19:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2a3b4c5d6e7f"
down_revision: Union[str, Sequence[str], None] = "448487941269"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the pago table with payment tracking fields.

    Schema:
        - id: auto-increment primary key
        - pedido_id: FK to pedido.id (which order this payment belongs to)
        - mp_payment_id: MercadoPago's payment ID (unique, nullable)
        - mp_status: payment status from MP (approved, pending, rejected, etc.)
        - mp_status_detail: detailed status description from MP
        - external_reference: unique reference sent to MP (UUID)
        - idempotency_key: unique key preventing double-charge (UUID)
        - transaction_amount: amount charged
        - payment_method_id: specific MP payment method used
        - created_at / updated_at: timestamps
    """
    op.create_table(
        "pago",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("mp_payment_id", sa.Integer(), nullable=True),
        sa.Column("mp_status", sa.String(length=30), nullable=False),
        sa.Column("mp_status_detail", sa.String(length=100), nullable=True),
        sa.Column("external_reference", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column(
            "transaction_amount",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
        ),
        sa.Column("payment_method_id", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            columns=["pedido_id"],
            refcolumns=["pedido.id"],
            name="fk_pago_pedido_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pago"),
        sa.UniqueConstraint("mp_payment_id", name="uq_pago_mp_payment_id"),
        sa.UniqueConstraint("external_reference", name="uq_pago_external_reference"),
        sa.UniqueConstraint("idempotency_key", name="uq_pago_idempotency_key"),
    )


def downgrade() -> None:
    """Drop the pago table."""
    op.drop_table("pago")
