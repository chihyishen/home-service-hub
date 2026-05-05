"""enforce trade_date and ex_dividend_date NOT NULL

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3g4h5i6
Create Date: 2026-05-05 11:00:00.000000

Locks down date columns the rest of the service treats as required:

- ``transactions.trade_date`` already has a server default of NOW(); flipping
  to NOT NULL prevents any client (or future migration) from ever leaving it
  blank. ``_resolve_sort_trade_date`` in app/services/portfolio_service.py
  assumes a non-NULL ``datetime``.
- ``dividends.ex_dividend_date`` is required by the API and used in summary
  cash-flow ordering and XIRR; rejecting NULL at the DB matches that contract.

Preflight ran before this migration; both queries returned 0 rows, so the
ALTER will not need a backfill step here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e2f3g4h5i6j7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3g4h5i6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "transactions",
        "trade_date",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "dividends",
        "ex_dividend_date",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "dividends",
        "ex_dividend_date",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )
    op.alter_column(
        "transactions",
        "trade_date",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
