"""add portfolio data constraints

Revision ID: b7a1c9d2e4f6
Revises: 570991c7b5b8
Create Date: 2026-05-04 15:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b7a1c9d2e4f6"
down_revision: Union[str, Sequence[str], None] = "570991c7b5b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_transactions_symbol_not_blank",
        "transactions",
        "length(trim(symbol)) > 0",
    )
    op.create_check_constraint(
        "ck_transactions_quantity_positive",
        "transactions",
        "quantity > 0",
    )
    op.create_check_constraint(
        "ck_transactions_price_positive",
        "transactions",
        "price > 0",
    )
    op.create_check_constraint(
        "ck_transactions_fee_nonnegative",
        "transactions",
        "coalesce(fee, 0) >= 0",
    )
    op.create_check_constraint(
        "ck_transactions_tax_nonnegative",
        "transactions",
        "coalesce(tax, 0) >= 0",
    )
    op.create_check_constraint(
        "ck_dividends_symbol_not_blank",
        "dividends",
        "length(trim(symbol)) > 0",
    )
    op.create_check_constraint(
        "ck_dividends_amount_positive",
        "dividends",
        "amount > 0",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_dividends_amount_positive", "dividends", type_="check")
    op.drop_constraint("ck_dividends_symbol_not_blank", "dividends", type_="check")
    op.drop_constraint("ck_transactions_tax_nonnegative", "transactions", type_="check")
    op.drop_constraint("ck_transactions_fee_nonnegative", "transactions", type_="check")
    op.drop_constraint("ck_transactions_price_positive", "transactions", type_="check")
    op.drop_constraint("ck_transactions_quantity_positive", "transactions", type_="check")
    op.drop_constraint("ck_transactions_symbol_not_blank", "transactions", type_="check")