"""accounting_retries: queue of failed accounting syncs for the daily retry job

Revision ID: y2m3n4o5p6q7
Revises: x1l2m3n4o5p6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "y2m3n4o5p6q7"
down_revision: Union[str, Sequence[str], None] = "x1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "accounting_retries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("accounting_id", sa.Integer(), nullable=True),
        sa.Column("item", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("accounting_retries")
