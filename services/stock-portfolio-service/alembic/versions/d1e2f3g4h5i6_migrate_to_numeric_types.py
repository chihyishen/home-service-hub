"""migrate_to_numeric_types

Revision ID: d1e2f3g4h5i6
Revises: c4d5e6f7a8b9
Create Date: 2026-05-05 10:00:00.000000

Aligns money columns with the application contract: every money value in
this service is a Python ``decimal.Decimal`` quantised to 2 decimal places.
The original schema stored these as ``DOUBLE PRECISION``, which silently
introduces float drift when read back into Python.

WARNING — USING cast truncation:

    ``<col>::numeric(12,2)`` rounds half-away-from-zero to 2 decimal places.
    Any pre-existing row with > 2 decimal places (e.g. a fee of 1.4250)
    would lose precision irreversibly during this upgrade.

    Run this preflight BEFORE applying upgrade() in any environment that
    might have such data (production, staging restored from prod):

        select count(*) from transactions
        where price is not null and price <> round(price::numeric, 2);
        -- repeat for transactions.fee, transactions.tax, dividends.amount

    Expect 0 rows. If non-zero, decide whether rounding is acceptable
    (probably yes for fee/tax broker rounding) or whether the affected
    rows need a manual cleanup commit before this migration runs.

The downgrade is reversible at the type level but will not restore the
sub-cent precision lost in upgrade(); document this when downgrading.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd1e2f3g4h5i6'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "transactions", "price",
        existing_type=postgresql.DOUBLE_PRECISION(),
        type_=sa.Numeric(12, 2),
        postgresql_using="price::numeric(12,2)",
        existing_nullable=False,
    )
    op.alter_column(
        "transactions", "fee",
        existing_type=postgresql.DOUBLE_PRECISION(),
        type_=sa.Numeric(12, 2),
        postgresql_using="fee::numeric(12,2)",
        existing_nullable=True,
    )
    op.alter_column(
        "transactions", "tax",
        existing_type=postgresql.DOUBLE_PRECISION(),
        type_=sa.Numeric(12, 2),
        postgresql_using="tax::numeric(12,2)",
        existing_nullable=True,
    )
    op.alter_column(
        "dividends", "amount",
        existing_type=postgresql.DOUBLE_PRECISION(),
        type_=sa.Numeric(12, 2),
        postgresql_using="amount::numeric(12,2)",
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "transactions", "price",
        existing_type=sa.Numeric(12, 2),
        type_=postgresql.DOUBLE_PRECISION(),
        postgresql_using="price::double precision",
        existing_nullable=False,
    )
    op.alter_column(
        "transactions", "fee",
        existing_type=sa.Numeric(12, 2),
        type_=postgresql.DOUBLE_PRECISION(),
        postgresql_using="fee::double precision",
        existing_nullable=True,
    )
    op.alter_column(
        "transactions", "tax",
        existing_type=sa.Numeric(12, 2),
        type_=postgresql.DOUBLE_PRECISION(),
        postgresql_using="tax::double precision",
        existing_nullable=True,
    )
    op.alter_column(
        "dividends", "amount",
        existing_type=sa.Numeric(12, 2),
        type_=postgresql.DOUBLE_PRECISION(),
        postgresql_using="amount::double precision",
        existing_nullable=False,
    )
