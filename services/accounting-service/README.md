# Agent Accounting Service

This is a FastAPI-based service for AI agent bookkeeping.

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update `DATABASE_URL` with your PostgreSQL credentials.

4. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Migrations

- Empty databases are bootstrapped with `alembic upgrade head`.
- Existing databases are handled conservatively by the baseline revision: it creates any missing accounting tables and only removes legacy columns when they are actually present, so running `alembic upgrade head` does not drop or recreate live tables.
- Revision `8a4c4f9b2d1b` backfills `transactions.category_id` and `subscriptions.category_id`, drops the legacy string `category` columns, and keeps category display data derived from the `categories` table.
- To inspect the current revision before upgrading, run:
   ```bash
   alembic current
   ```

## Category Contract

- Transaction and subscription create payloads must provide `categoryId`.
- API responses expose `categoryId` and `categoryName`; they no longer expose a top-level `category` string field.
- Category rename and merge flows update only foreign keys and read display names from the joined category relation.

## API Documentation

Once the server is running, you can access:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
