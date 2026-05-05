"""add portfolio list indexes

Revision ID: c4d5e6f7a8b9
Revises: b7a1c9d2e4f6
Create Date: 2026-05-04 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b7a1c9d2e4f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_transactions_trade_date", "transactions", ["trade_date"])
    op.create_index("ix_dividends_ex_dividend_date", "dividends", ["ex_dividend_date"])
    op.create_index("ix_transactions_symbol_trade_date", "transactions", ["symbol", "trade_date"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_transactions_symbol_trade_date", table_name="transactions")
    op.drop_index("ix_dividends_ex_dividend_date", table_name="dividends")
    op.drop_index("ix_transactions_trade_date", table_name="transactions")