"""transactions.external_ref: idempotency key for entries synced from other services

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("external_ref", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_transactions_external_ref", "transactions", ["external_ref"])


def downgrade() -> None:
    op.drop_constraint("uq_transactions_external_ref", "transactions", type_="unique")
    op.drop_column("transactions", "external_ref")
