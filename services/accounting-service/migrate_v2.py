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

with engine.connect() as conn:
    print("Migrating database...")
    # Add column if it doesn't exist
    conn.execute(text("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS default_payment_method VARCHAR DEFAULT 'Apple Pay';"))
    # Drop redundant table
    conn.execute(text("DROP TABLE IF EXISTS payment_routes CASCADE;"))
    conn.commit()
    print("Migration completed.")
