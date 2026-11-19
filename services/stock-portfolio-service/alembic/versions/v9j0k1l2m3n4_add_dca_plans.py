"""add dca_plans table and transactions.is_estimated

Revision ID: v9j0k1l2m3n4
Revises: u8i9j0k1l2m3
Create Date: 2026-11-19 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "v9j0k1l2m3n4"
down_revision: Union[str, Sequence[str], None] = "u8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("is_estimated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "dca_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("day_of_month", sa.Integer(), nullable=False),
        sa.Column("fee", sa.Numeric(12, 2), nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_executed_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="ck_dca_plans_amount_positive"),
        sa.CheckConstraint("day_of_month BETWEEN 1 AND 31", name="ck_dca_plans_day_range"),
        sa.CheckConstraint("fee >= 0", name="ck_dca_plans_fee_nonnegative"),
    )


def downgrade() -> None:
    op.drop_table("dca_plans")
    op.drop_column("transactions", "is_estimated")
