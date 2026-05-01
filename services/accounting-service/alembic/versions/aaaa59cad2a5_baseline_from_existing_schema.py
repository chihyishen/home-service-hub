"""baseline from existing schema

Revision ID: aaaa59cad2a5
Revises: 
Create Date: 2026-04-20 15:57:39.037424

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


def _timestamp_columns() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
    ]


def _ensure_table(inspector: sa.Inspector, table_name: str, create_table: callable) -> None:
    if not inspector.has_table(table_name):
        create_table()


def _ensure_index(inspector: sa.Inspector, table_name: str, index_name: str, columns: list[str]) -> None:
    existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, columns, unique=False)


def _drop_column_if_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> None:
    if not inspector.has_table(table_name):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        op.drop_column(table_name, column_name)

# revision identifiers, used by Alembic.
revision: str = 'aaaa59cad2a5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bootstrap the full accounting schema and reconcile legacy columns when present."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    _ensure_table(
        inspector,
        "categories",
        lambda: op.create_table(
            "categories",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=True, unique=True),
            sa.Column("color", sa.String(), nullable=True),
            *_timestamp_columns(),
        ),
    )
    _ensure_table(
        inspector,
        "credit_cards",
        lambda: op.create_table(
            "credit_cards",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=True, unique=True),
            sa.Column("billing_day", sa.Integer(), nullable=True),
            sa.Column("reward_cycle_type", sa.String(), nullable=True),
            sa.Column("alert_threshold", sa.Integer(), nullable=True),
            sa.Column("default_payment_method", sa.String(), nullable=True),
            *_timestamp_columns(),
        ),
    )
    _ensure_table(
        inspector,
        "payment_methods",
        lambda: op.create_table(
            "payment_methods",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=True, unique=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            *_timestamp_columns(),
        ),
    )
    _ensure_table(
        inspector,
        "subscriptions",
        lambda: op.create_table(
            "subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("amount", sa.Integer(), nullable=True),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
            sa.Column("sub_type", sa.String(), nullable=True),
            sa.Column("payment_method", sa.String(), nullable=True),
            sa.Column("day_of_month", sa.Integer(), nullable=True),
            sa.Column("card_id", sa.Integer(), sa.ForeignKey("credit_cards.id"), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=True),
            *_timestamp_columns(),
        ),
    )
    _ensure_table(
        inspector,
        "installments",
        lambda: op.create_table(
            "installments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("total_amount", sa.Integer(), nullable=True),
            sa.Column("monthly_amount", sa.Integer(), nullable=True),
            sa.Column("payment_method", sa.String(), nullable=True),
            sa.Column("total_periods", sa.Integer(), nullable=True),
            sa.Column("remaining_periods", sa.Integer(), nullable=True),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("card_id", sa.Integer(), sa.ForeignKey("credit_cards.id"), nullable=True),
            *_timestamp_columns(),
        ),
    )
    _ensure_table(
        inspector,
        "transactions",
        lambda: op.create_table(
            "transactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=True),
            sa.Column("category", sa.String(), nullable=True),
            sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
            sa.Column("item", sa.String(), nullable=True),
            sa.Column("paid_amount", sa.Integer(), nullable=True),
            sa.Column("transaction_amount", sa.Integer(), nullable=True),
            sa.Column("payment_method", sa.String(), nullable=True),
            sa.Column("card_id", sa.Integer(), sa.ForeignKey("credit_cards.id"), nullable=True),
            sa.Column("transaction_type", sa.String(), nullable=True),
            sa.Column("note", sa.String(), nullable=True),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("related_transaction_id", sa.Integer(), sa.ForeignKey("transactions.id"), nullable=True),
            sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("subscriptions.id"), nullable=True),
            sa.Column("installment_id", sa.Integer(), sa.ForeignKey("installments.id"), nullable=True),
            *_timestamp_columns(),
        ),
    )

    inspector = sa.inspect(bind)
    _ensure_index(inspector, "categories", "ix_categories_id", ["id"])
    _ensure_index(inspector, "categories", "ix_categories_name", ["name"])
    _ensure_index(inspector, "credit_cards", "ix_credit_cards_id", ["id"])
    _ensure_index(inspector, "credit_cards", "ix_credit_cards_name", ["name"])
    _ensure_index(inspector, "payment_methods", "ix_payment_methods_id", ["id"])
    _ensure_index(inspector, "payment_methods", "ix_payment_methods_name", ["name"])
    _ensure_index(inspector, "subscriptions", "ix_subscriptions_id", ["id"])
    _ensure_index(inspector, "installments", "ix_installments_id", ["id"])
    _ensure_index(inspector, "transactions", "ix_transactions_id", ["id"])
    _ensure_index(inspector, "transactions", "ix_transactions_category", ["category"])

    inspector = sa.inspect(bind)
    _drop_column_if_exists(inspector, "credit_cards", "reward_rules")
    inspector = sa.inspect(bind)
    _drop_column_if_exists(inspector, "transactions", "status")


def downgrade() -> None:
    """Restore legacy columns without dropping current tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("transactions"):
        columns = {column["name"] for column in inspector.get_columns("transactions")}
        if "status" not in columns:
            op.add_column("transactions", sa.Column("status", sa.String(), nullable=True))

    inspector = sa.inspect(bind)
    if inspector.has_table("credit_cards"):
        columns = {column["name"] for column in inspector.get_columns("credit_cards")}
        if "reward_rules" not in columns:
            op.add_column("credit_cards", sa.Column("reward_rules", sa.JSON(), nullable=True))
