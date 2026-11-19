"""transactions.accounting_transaction_id: link DCA buys to accounting entries

Revision ID: w0k1l2m3n4o5
Revises: v9j0k1l2m3n4
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w0k1l2m3n4o5"
down_revision: Union[str, Sequence[str], None] = "v9j0k1l2m3n4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("accounting_transaction_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "accounting_transaction_id")
