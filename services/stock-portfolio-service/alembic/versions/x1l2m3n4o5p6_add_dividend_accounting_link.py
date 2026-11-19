"""dividends.accounting_transaction_id: link dividends to accounting income

Revision ID: x1l2m3n4o5p6
Revises: w0k1l2m3n4o5
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "x1l2m3n4o5p6"
down_revision: Union[str, Sequence[str], None] = "w0k1l2m3n4o5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dividends", sa.Column("accounting_transaction_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("dividends", "accounting_transaction_id")
