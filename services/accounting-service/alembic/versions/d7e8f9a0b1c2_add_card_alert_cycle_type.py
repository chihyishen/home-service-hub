"""add independent alert cycle type to credit cards

Revision ID: d7e8f9a0b1c2
Revises: c1d2e3f4a5b6
Create Date: 2026-07-10 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not inspector.has_table(table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_column(sa.inspect(bind), "credit_cards", "alert_cycle_type"):
        op.add_column("credit_cards", sa.Column("alert_cycle_type", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if _has_column(sa.inspect(bind), "credit_cards", "alert_cycle_type"):
        op.drop_column("credit_cards", "alert_cycle_type")
