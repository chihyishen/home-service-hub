"""add durable portfolio recalculation state

Revision ID: u8i9j0k1l2m3
Revises: t7i8j9k0l1m2
Create Date: 2026-10-17 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "u8i9j0k1l2m3"
down_revision: Union[str, Sequence[str], None] = "t7i8j9k0l1m2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolio_recalc_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("recalc_from", sa.Date(), nullable=True),
        sa.Column("recalc_to", sa.Date(), nullable=True),
        sa.Column("touched_symbols", sa.JSON(), nullable=False),
        sa.Column("current_step", sa.String(length=64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    state_table = sa.table(
        "portfolio_recalc_state",
        sa.column("id", sa.Integer()),
        sa.column("generation", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("mode", sa.String()),
        sa.column("touched_symbols", sa.JSON()),
    )
    op.bulk_insert(
        state_table,
        [{"id": 1, "generation": 0, "status": "idle", "mode": "snapshots", "touched_symbols": []}],
    )


def downgrade() -> None:
    op.drop_table("portfolio_recalc_state")
