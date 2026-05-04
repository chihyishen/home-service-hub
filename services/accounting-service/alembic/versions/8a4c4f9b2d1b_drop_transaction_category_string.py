"""drop transaction and subscription category string columns

Revision ID: 8a4c4f9b2d1b
Revises: aaaa59cad2a5
Create Date: 2026-05-04 16:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a4c4f9b2d1b"
down_revision: Union[str, Sequence[str], None] = "aaaa59cad2a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    if not inspector.has_table(table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _ensure_categories_name_unique(inspector: sa.Inspector) -> None:
    unique_constraints = inspector.get_unique_constraints("categories")
    if any(set(constraint.get("column_names") or []) == {"name"} for constraint in unique_constraints):
        return

    indexes = inspector.get_indexes("categories")
    if any(index.get("unique") and set(index.get("column_names") or []) == {"name"} for index in indexes):
        return

    op.create_unique_constraint("uq_categories_name", "categories", ["name"])


def _backfill_category_ids(connection: sa.Connection, table_name: str) -> None:
    connection.execute(
        sa.text(
            f"""
            UPDATE {table_name} AS row
            SET category_id = c.id
            FROM categories AS c
            WHERE row.category_id IS NULL
              AND row.category IS NOT NULL
              AND row.category = c.name
            """
        )
    )
    connection.execute(
        sa.text(
            f"""
            INSERT INTO categories (name)
            SELECT DISTINCT row.category
            FROM {table_name} AS row
            WHERE row.category_id IS NULL
              AND row.category IS NOT NULL
            ON CONFLICT (name) DO NOTHING
            """
        )
    )
    connection.execute(
        sa.text(
            f"""
            UPDATE {table_name} AS row
            SET category_id = c.id
            FROM categories AS c
            WHERE row.category_id IS NULL
              AND row.category IS NOT NULL
              AND row.category = c.name
            """
        )
    )


def _assert_no_null_category_ids(connection: sa.Connection, table_name: str) -> None:
    remaining = connection.execute(
        sa.text(f"SELECT COUNT(*) FROM {table_name} WHERE category_id IS NULL")
    ).scalar_one()
    if remaining:
        raise RuntimeError(f"{table_name}.category_id still contains NULL after backfill: {remaining}")


def _backfill_category_names(connection: sa.Connection, table_name: str) -> None:
    connection.execute(
        sa.text(
            f"""
            UPDATE {table_name} AS row
            SET category = c.name
            FROM categories AS c
            WHERE row.category_id = c.id
            """
        )
    )


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    _ensure_categories_name_unique(inspector)

    for table_name in ("transactions", "subscriptions"):
        inspector = sa.inspect(connection)
        if not inspector.has_table(table_name):
            continue

        if _has_column(inspector, table_name, "category"):
            _backfill_category_ids(connection, table_name)

        _assert_no_null_category_ids(connection, table_name)
        op.alter_column(table_name, "category_id", existing_type=sa.Integer(), nullable=False)

        inspector = sa.inspect(connection)
        if _has_column(inspector, table_name, "category"):
            op.drop_column(table_name, "category")


def downgrade() -> None:
    connection = op.get_bind()

    for table_name in ("transactions", "subscriptions"):
        inspector = sa.inspect(connection)
        if not inspector.has_table(table_name):
            continue

        if not _has_column(inspector, table_name, "category"):
            op.add_column(table_name, sa.Column("category", sa.String(), nullable=True))

        _backfill_category_names(connection, table_name)