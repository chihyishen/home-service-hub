# Alembic Migrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `Base.metadata.create_all()` in both Python services with Alembic-managed migrations, so schema changes are versioned, reversible, and safe to run against a live database.

**Architecture:** Each Python service gets its own `alembic/` directory with its own `versions/` folder. The first migration is an auto-generated baseline from the existing models. `main.py` no longer calls `create_all()` — instead, Alembic `upgrade head` runs at startup or via CLI. The shared-lib is NOT responsible for migrations (each service owns its schema).

**Tech Stack:** Alembic, SQLAlchemy, existing model definitions.

**Prerequisites:** Plan 2 (shared-lib refactor) should be merged first, since this plan modifies `main.py` which was rewritten in Plan 2.

---

## File Structure

- Create: `services/accounting-service/alembic.ini`
- Create: `services/accounting-service/alembic/env.py`
- Create: `services/accounting-service/alembic/script.py.mako`
- Create: `services/accounting-service/alembic/versions/` (initially empty, auto-generated baseline)
- Create: `services/stock-portfolio-service/alembic.ini`
- Create: `services/stock-portfolio-service/alembic/env.py`
- Create: `services/stock-portfolio-service/alembic/script.py.mako`
- Create: `services/stock-portfolio-service/alembic/versions/`
- Modify: `services/accounting-service/app/main.py` — remove `Base.metadata.create_all()`
- Modify: `services/stock-portfolio-service/app/main.py` — remove `Base.metadata.create_all()`
- Modify: `services/accounting-service/requirements.txt` — add `alembic`
- Modify: `services/stock-portfolio-service/requirements.txt` — add `alembic`

---

### Task 1: Add Alembic to accounting-service

**Files:**
- Modify: `services/accounting-service/requirements.txt`
- Create: `services/accounting-service/alembic.ini`
- Create: `services/accounting-service/alembic/env.py`
- Create: `services/accounting-service/alembic/script.py.mako`

- [ ] **Step 1: Add alembic dependency**

Edit `services/accounting-service/requirements.txt`. Add `alembic` to the end:

```
-e ../shared-python-lib
fastapi
uvicorn
requests
alembic
```

Install:

```bash
cd services/accounting-service
pip install alembic
```

- [ ] **Step 2: Initialize alembic**

```bash
cd services/accounting-service
alembic init alembic
```

This creates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 3: Configure alembic.ini**

Edit `services/accounting-service/alembic.ini`. Find the line:

```ini
sqlalchemy.url = driver://user:pass@localhost/dbname
```

Replace with (empty string — we load URL from code):

```ini
sqlalchemy.url =
```

- [ ] **Step 4: Configure alembic/env.py for auto-generation**

Replace the **entire** content of `services/accounting-service/alembic/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import SQLALCHEMY_DATABASE_URL
from app.database import Base

# Import all models so Base.metadata knows about them
import app.models.transaction  # noqa: F401
import app.models.card  # noqa: F401
import app.models.category  # noqa: F401
import app.models.payment_method  # noqa: F401
import app.models.recurring  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Generate baseline migration**

Make sure Postgres is running (`docker compose up -d postgres`), then:

```bash
cd services/accounting-service
alembic revision --autogenerate -m "baseline from existing schema"
```

This creates a file like `alembic/versions/xxxx_baseline_from_existing_schema.py`. Inspect it:

```bash
cat alembic/versions/*baseline*.py
```

Verify it contains `CREATE TABLE` for `transactions`, `credit_cards`, `categories`, `payment_methods`, `subscriptions`, `installments`. The `upgrade()` function should have all the table definitions; `downgrade()` should drop them.

- [ ] **Step 6: Stamp database as current (don't re-run the baseline)**

Since the tables already exist in your database, stamp the current state:

```bash
alembic stamp head
```

This writes the migration version to `alembic_version` table without running it.

- [ ] **Step 7: Commit**

```bash
git add services/accounting-service/requirements.txt \
        services/accounting-service/alembic.ini \
        services/accounting-service/alembic/env.py \
        services/accounting-service/alembic/script.py.mako \
        services/accounting-service/alembic/versions/
git commit -m "feat(accounting): add Alembic with baseline migration"
```

---

### Task 2: Add Alembic to stock-portfolio-service

**Files:**
- Modify: `services/stock-portfolio-service/requirements.txt`
- Create: `services/stock-portfolio-service/alembic.ini`
- Create: `services/stock-portfolio-service/alembic/env.py`
- Create: `services/stock-portfolio-service/alembic/script.py.mako`

- [ ] **Step 1: Add alembic dependency**

Edit `services/stock-portfolio-service/requirements.txt`:

```
-e ../shared-python-lib
fastapi
uvicorn
requests
alembic
```

```bash
cd services/stock-portfolio-service
pip install alembic
```

- [ ] **Step 2: Initialize alembic**

```bash
cd services/stock-portfolio-service
alembic init alembic
```

- [ ] **Step 3: Configure alembic.ini**

Same as Task 1 Step 3: set `sqlalchemy.url =` (empty).

- [ ] **Step 4: Configure alembic/env.py**

Replace the **entire** content of `services/stock-portfolio-service/alembic/env.py` with:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import SQLALCHEMY_DATABASE_URL
from app.database import Base

# Import all models so Base.metadata knows about them
import app.models.portfolio  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Generate baseline migration**

```bash
cd services/stock-portfolio-service
alembic revision --autogenerate -m "baseline from existing schema"
```

Inspect the generated file. Should have `transactions` and `dividends` tables.

- [ ] **Step 6: Stamp database**

```bash
alembic stamp head
```

- [ ] **Step 7: Commit**

```bash
git add services/stock-portfolio-service/requirements.txt \
        services/stock-portfolio-service/alembic.ini \
        services/stock-portfolio-service/alembic/env.py \
        services/stock-portfolio-service/alembic/script.py.mako \
        services/stock-portfolio-service/alembic/versions/
git commit -m "feat(stock): add Alembic with baseline migration"
```

---

### Task 3: Remove `create_all()` from both services

**Files:**
- Modify: `services/accounting-service/app/main.py`
- Modify: `services/stock-portfolio-service/app/main.py`

- [ ] **Step 1: Edit accounting main.py**

In `services/accounting-service/app/main.py` (after Plan 2 refactor), find and **delete** these lines:

```python
# Create tables (will be replaced by Alembic in Plan 3)
Base.metadata.create_all(bind=engine)
```

Also remove the `Base` import if it's no longer used. The file should now look like:

```python
from shared_lib import create_app

from .database import engine, get_db
from .routers import transactions, cards, recurring, categories, payment_methods

app = create_app(
    title="Home Service Hub - Accounting API",
    description="記帳與財務管理微服務。",
    version="1.2.0",
    routers=[
        transactions.router,
        cards.router,
        recurring.router,
        categories.router,
        payment_methods.router,
    ],
    get_db=get_db,
    engine=engine,
    otel_service_name_env="OTEL_SERVICE_NAME_ACCOUNTING",
    otel_strict=True,
)
```

- [ ] **Step 2: Edit stock-portfolio main.py**

Same treatment. `services/stock-portfolio-service/app/main.py` becomes:

```python
from shared_lib import create_app

from .database import engine, get_db
from .routers import portfolio

app = create_app(
    title="Home Service Hub - Stock Portfolio API",
    description="投資組合管理微服務。",
    version="1.0.0",
    routers=[portfolio.router],
    get_db=get_db,
    engine=engine,
    otel_service_name_env="OTEL_SERVICE_NAME_STOCK",
    otel_strict=False,
)
```

- [ ] **Step 3: Run tests on both services**

```bash
cd services/accounting-service && pytest -v
cd ../stock-portfolio-service && pytest -v
```

Expected: all pass. Tests use SQLite in-memory with `create_all` in conftest, so they're unaffected.

- [ ] **Step 4: Manual verification — run Alembic upgrade on a fresh DB**

To verify the migration works on a clean database:

```bash
cd services/accounting-service

# Create a temp test database
docker compose exec postgres psql -U ${POSTGRES_USER} -c "CREATE DATABASE accounting_test_migration;"

# Point at the temp DB and migrate
ACCOUNTING_DB=accounting_test_migration alembic upgrade head

# Verify tables exist
docker compose exec postgres psql -U ${POSTGRES_USER} -d accounting_test_migration -c "\dt"

# Cleanup
docker compose exec postgres psql -U ${POSTGRES_USER} -c "DROP DATABASE accounting_test_migration;"
```

Expected: `\dt` shows all tables from the baseline migration.

- [ ] **Step 5: Commit**

```bash
git add services/accounting-service/app/main.py \
        services/stock-portfolio-service/app/main.py
git commit -m "refactor: remove create_all(), schema managed by Alembic only"
```

---

### Task 4: Update test conftest to use Alembic for test DB (optional but recommended)

**Files:**
- Modify: `services/accounting-service/tests/conftest.py`
- Modify: `services/stock-portfolio-service/tests/conftest.py`

Note: This task is **optional**. Tests currently use `Base.metadata.create_all()` with SQLite in-memory, which works. However, if you want test DB schema to exactly match migrations, replace `create_all` with Alembic. For now, keeping `create_all` in test fixtures is acceptable — it ensures tests always run the latest schema without a migration step.

- [ ] **Step 1: Add a comment in conftest documenting this decision**

In both `tests/conftest.py`, add a comment above the `create_all` line:

```python
    # NOTE: Tests use create_all() instead of Alembic for speed.
    # Prod uses Alembic migrations only (see alembic/ directory).
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 2: Commit**

```bash
git add services/accounting-service/tests/conftest.py \
        services/stock-portfolio-service/tests/conftest.py
git commit -m "docs: clarify test DB uses create_all, prod uses Alembic"
```

---

## Self-Review Checklist

- [ ] `alembic/env.py` imports ALL model modules (not just some) so autogenerate catches every table
- [ ] `alembic.ini` has empty `sqlalchemy.url` — URL set programmatically from app config
- [ ] `alembic stamp head` was run on existing database (not `alembic upgrade head`, which would fail on existing tables)
- [ ] `main.py` no longer calls `create_all()` in either service
- [ ] Test `conftest.py` still uses `create_all()` (for speed) with a comment explaining why
- [ ] Baseline migration `downgrade()` properly drops all tables

## Out of Scope

- Setting up Alembic for the Java/Spring Boot inventory-api (already uses Flyway — see `application.yml`)
- Auto-running `alembic upgrade head` at service startup (can be added later; for now run manually or in Dockerfile entrypoint)
- Alembic migration tests (the manual verification step is sufficient for a baseline)
