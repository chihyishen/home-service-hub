import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(env_path, override=True)


def get_database_url() -> str:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("DB_HOST")
    port = os.getenv("POSTGRES_PORT")
    db_name = os.getenv("ACCOUNTING_DB")
    missing = [k for k, v in {
        "POSTGRES_USER": user,
        "POSTGRES_PASSWORD": password,
        "DB_HOST": host,
        "POSTGRES_PORT": port,
        "ACCOUNTING_DB": db_name
    }.items() if not v]
    if missing:
        raise ValueError(f"Missing required env vars: {', '.join(missing)} (env: {env_path})")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


engine = create_engine(get_database_url())


def column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table_name
              AND column_name = :column_name
            LIMIT 1
            """
        ),
        {"table_name": table, "column_name": column},
    ).scalar()
    return bool(result)


with engine.connect() as conn:
    print("Migrating database to v3 (transaction amount field renaming)...")

    if column_exists(conn, "transactions", "actual_swipe") and not column_exists(conn, "transactions", "transaction_amount"):
        conn.execute(text("ALTER TABLE transactions RENAME COLUMN actual_swipe TO transaction_amount;"))
        print("Renamed transactions.actual_swipe -> transaction_amount")

    if column_exists(conn, "transactions", "personal_amount") and not column_exists(conn, "transactions", "paid_amount"):
        conn.execute(text("ALTER TABLE transactions RENAME COLUMN personal_amount TO paid_amount;"))
        print("Renamed transactions.personal_amount -> paid_amount")

    conn.commit()
    print("Migration v3 completed.")
