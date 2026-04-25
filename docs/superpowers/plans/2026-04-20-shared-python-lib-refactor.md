# Shared Python Library Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract duplicated boilerplate from accounting-service and stock-portfolio-service into `shared-python-lib`, so each service's `main.py` becomes a 10-line config file instead of a copy-pasted template.

**Architecture:** Add three modules to `shared_lib`: (1) `config.py` with Pydantic `BaseSettings` for env management, (2) `errors.py` with a global exception handler + `ErrorResponse` schema, (3) `app_factory.py` to bootstrap FastAPI (CORS, routers, tracing, error handler) in one call. Services keep their own `database.py` (different pool configs is intentional per-service tuning), `models/`, `routers/`, `schemas/`, `services/`. The refactor is import-only — zero behaviour change to existing endpoints.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2 `BaseSettings`, SQLAlchemy, existing `shared_lib` package.

**Prerequisites:** Plan 1 (health-checks) should be merged first, since this plan will include the health router registration in the factory.

---

## File Structure

- Create: `services/shared-python-lib/shared_lib/config.py` — Pydantic BaseSettings for shared env vars
- Create: `services/shared-python-lib/shared_lib/errors.py` — global exception handler + ErrorResponse model
- Create: `services/shared-python-lib/shared_lib/app_factory.py` — `create_app()` factory
- Create: `services/shared-python-lib/shared_lib/health.py` — shared health router (replaces per-service copies from Plan 1)
- Create: `services/shared-python-lib/tests/test_errors.py`
- Create: `services/shared-python-lib/tests/test_app_factory.py`
- Modify: `services/shared-python-lib/shared_lib/__init__.py` — public exports
- Modify: `services/shared-python-lib/pyproject.toml` — add `pydantic-settings` dependency
- Modify: `services/accounting-service/app/main.py` — replace boilerplate with `create_app()`
- Modify: `services/stock-portfolio-service/app/main.py` — same
- Delete: `services/accounting-service/app/tracing.py` — no longer needed (factory handles tracing)
- Delete: `services/stock-portfolio-service/app/tracing.py` — same
- Delete: `services/accounting-service/app/routers/health.py` — replaced by shared health router
- Delete: `services/stock-portfolio-service/app/routers/health.py` — same

---

### Task 1: Add `pydantic-settings` dependency

**Files:**
- Modify: `services/shared-python-lib/pyproject.toml`

- [ ] **Step 1: Add dependency**

Edit `services/shared-python-lib/pyproject.toml`. In the `dependencies` list, add:

```toml
    "pydantic-settings>=2.0",
```

Full `dependencies` should look like:

```toml
dependencies = [
    "sqlalchemy",
    "psycopg2-binary",
    "python-dotenv",
    "pydantic-settings>=2.0",
    "opentelemetry-api",
    "opentelemetry-sdk",
    "opentelemetry-exporter-otlp",
    "opentelemetry-instrumentation-fastapi",
    "opentelemetry-instrumentation-sqlalchemy",
    "opentelemetry-instrumentation-logging",
    "opentelemetry-instrumentation-requests",
]
```

- [ ] **Step 2: Reinstall shared lib in both services**

```bash
cd services/accounting-service && pip install -e ../shared-python-lib
cd ../stock-portfolio-service && pip install -e ../shared-python-lib
```

- [ ] **Step 3: Commit**

```bash
git add services/shared-python-lib/pyproject.toml
git commit -m "chore(shared-lib): add pydantic-settings dependency"
```

---

### Task 2: Create `config.py` — shared settings

**Files:**
- Create: `services/shared-python-lib/shared_lib/config.py`

- [ ] **Step 1: Create config module**

Create `services/shared-python-lib/shared_lib/config.py`:

```python
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_root_env() -> str:
    """Walk up from CWD to find root .env (contains docker-compose.yml)."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / "docker-compose.yml").exists():
            return str(parent / ".env")
    return str(current / ".env")


class SharedSettings(BaseSettings):
    """Base settings all services inherit. Loads from root .env automatically."""

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", _find_root_env()),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Postgres
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    db_host: str = "localhost"
    postgres_port: int = 5432

    # CORS
    allowed_origins: str = "http://localhost:4200"

    # OpenTelemetry (optional — services that don't need tracing can skip)
    otel_collector_endpoint_grpc: str | None = None

    def get_allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def get_database_url(self, db_name: str) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.db_host}:{self.postgres_port}/{db_name}"
        )
```

- [ ] **Step 2: Quick smoke test**

```bash
cd services/shared-python-lib
python -c "from shared_lib.config import SharedSettings; s = SharedSettings(); print(s.db_host)"
```

Expected: prints `localhost` (or whatever DB_HOST is in `.env`).

- [ ] **Step 3: Commit**

```bash
git add services/shared-python-lib/shared_lib/config.py
git commit -m "feat(shared-lib): add SharedSettings pydantic config"
```

---

### Task 3: Create `errors.py` — global exception handler

**Files:**
- Create: `services/shared-python-lib/shared_lib/errors.py`
- Create: `services/shared-python-lib/tests/test_errors.py`

- [ ] **Step 1: Write failing test**

Create `services/shared-python-lib/tests/test_errors.py`:

```python
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from shared_lib.errors import register_error_handlers


@pytest.fixture()
def app():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/ok")
    def ok():
        return {"msg": "ok"}

    @app.get("/http-error")
    def http_error():
        raise HTTPException(status_code=422, detail="bad input")

    @app.get("/unexpected")
    def unexpected():
        raise RuntimeError("boom")

    return app


@pytest.fixture()
def client(app):
    return TestClient(app, raise_server_exceptions=False)


def test_normal_response_unaffected(client):
    resp = client.get("/ok")
    assert resp.status_code == 200
    assert resp.json() == {"msg": "ok"}


def test_http_exception_returns_standard_shape(client):
    resp = client.get("/http-error")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == 422
    assert body["message"] == "bad input"
    assert "trace_id" in body


def test_unhandled_exception_returns_500(client):
    resp = client.get("/unexpected")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == 500
    assert "內部伺服器錯誤" in body["message"] or "Internal" in body["message"]
    assert "trace_id" in body
```

- [ ] **Step 2: Run test — verify fail**

```bash
cd services/shared-python-lib
pip install fastapi httpx  # httpx needed by TestClient
pytest tests/test_errors.py -v
```

Expected: ImportError (module doesn't exist yet).

- [ ] **Step 3: Implement errors module**

Create `services/shared-python-lib/shared_lib/errors.py`:

```python
from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from opentelemetry import trace

logger = logging.getLogger(__name__)


def _get_trace_id() -> str | None:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if ctx and ctx.trace_id:
        return format(ctx.trace_id, "032x")
    return None


def _error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": status_code,
            "message": message,
            "trace_id": _get_trace_id(),
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return _error_response(exc.status_code, detail)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _error_response(500, "內部伺服器錯誤，請稍後再試。")
```

- [ ] **Step 4: Run test — verify pass**

```bash
pytest tests/test_errors.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add services/shared-python-lib/shared_lib/errors.py \
        services/shared-python-lib/tests/test_errors.py
git commit -m "feat(shared-lib): add global error handler with standard error shape"
```

---

### Task 4: Create shared health router

**Files:**
- Create: `services/shared-python-lib/shared_lib/health.py`

This replaces the per-service `routers/health.py` from Plan 1.

- [ ] **Step 1: Create health module**

Create `services/shared-python-lib/shared_lib/health.py`:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session


def create_health_router(get_db) -> APIRouter:
    """Create a health router. Pass the service's get_db dependency."""
    router = APIRouter(tags=["health"])

    @router.get("/health")
    def liveness():
        return {"status": "ok"}

    @router.get("/health/ready")
    def readiness(db: Session = Depends(get_db)):
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ok", "database": "ok"}
        except Exception as exc:
            return {"status": "degraded", "database": f"error: {exc.__class__.__name__}"}

    return router
```

- [ ] **Step 2: Commit**

```bash
git add services/shared-python-lib/shared_lib/health.py
git commit -m "feat(shared-lib): add shared health router factory"
```

---

### Task 5: Create `app_factory.py`

**Files:**
- Create: `services/shared-python-lib/shared_lib/app_factory.py`
- Create: `services/shared-python-lib/tests/test_app_factory.py`

- [ ] **Step 1: Write failing test**

Create `services/shared-python-lib/tests/test_app_factory.py`:

```python
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from shared_lib.app_factory import create_app


@pytest.fixture()
def dummy_router():
    router = APIRouter()

    @router.get("/dummy")
    def dummy():
        return {"msg": "hello"}

    return router


@pytest.fixture()
def mock_get_db():
    return MagicMock()


def test_create_app_includes_routers(dummy_router, mock_get_db):
    app = create_app(
        title="Test Service",
        version="0.0.1",
        routers=[dummy_router],
        get_db=mock_get_db,
    )
    client = TestClient(app)
    resp = client.get("/dummy")
    assert resp.status_code == 200
    assert resp.json() == {"msg": "hello"}


def test_create_app_has_health_endpoint(dummy_router, mock_get_db):
    app = create_app(
        title="Test Service",
        version="0.0.1",
        routers=[dummy_router],
        get_db=mock_get_db,
    )
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_app_error_handler_shapes_response(dummy_router, mock_get_db):
    error_router = APIRouter()

    @error_router.get("/fail")
    def fail():
        raise ValueError("boom")

    app = create_app(
        title="Test",
        version="0.0.1",
        routers=[dummy_router, error_router],
        get_db=mock_get_db,
    )
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/fail")
    assert resp.status_code == 500
    assert resp.json()["code"] == 500
```

- [ ] **Step 2: Run test — verify fail**

```bash
cd services/shared-python-lib
pytest tests/test_app_factory.py -v
```

Expected: ImportError.

- [ ] **Step 3: Implement app factory**

Create `services/shared-python-lib/shared_lib/app_factory.py`:

```python
from __future__ import annotations

from typing import Callable, Sequence

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine

from .config import SharedSettings
from .errors import register_error_handlers
from .health import create_health_router
from .tracing import setup_tracing


def create_app(
    *,
    title: str,
    version: str,
    routers: Sequence[APIRouter],
    get_db: Callable,
    description: str = "",
    engine: Engine | None = None,
    otel_service_name_env: str | None = None,
    otel_strict: bool = False,
    settings: SharedSettings | None = None,
) -> FastAPI:
    """Bootstrap a FastAPI app with CORS, error handling, tracing, and health routes."""
    if settings is None:
        settings = SharedSettings()

    app = FastAPI(title=title, description=description, version=version)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_allowed_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handling (before routers so it catches all)
    register_error_handlers(app)

    # Business routers
    for router in routers:
        app.include_router(router)

    # Health
    app.include_router(create_health_router(get_db))

    # Root
    @app.get("/")
    async def root():
        return {"message": f"Welcome to {title}", "docs": "/docs"}

    # Tracing (after all routers registered so FastAPIInstrumentor picks them up)
    if otel_service_name_env and engine:
        setup_tracing(
            service_name_env=otel_service_name_env,
            strict=otel_strict,
            app=app,
            engine=engine,
        )

    return app
```

- [ ] **Step 4: Run test — verify pass**

```bash
pytest tests/test_app_factory.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Update `__init__.py` exports**

Edit `services/shared-python-lib/shared_lib/__init__.py`:

```python
from .app_factory import create_app
from .config import SharedSettings
from .database import Base, TimestampMixin, get_database_url, create_db_engine, get_db
from .errors import register_error_handlers
from .health import create_health_router
from .tracing import setup_tracing, get_tracer
```

- [ ] **Step 6: Commit**

```bash
git add services/shared-python-lib/shared_lib/app_factory.py \
        services/shared-python-lib/shared_lib/__init__.py \
        services/shared-python-lib/tests/test_app_factory.py
git commit -m "feat(shared-lib): add create_app() factory with CORS, errors, health, tracing"
```

---

### Task 6: Migrate accounting-service to use factory

**Files:**
- Modify: `services/accounting-service/app/main.py`
- Delete: `services/accounting-service/app/tracing.py`
- Delete: `services/accounting-service/app/routers/health.py` (from Plan 1)

- [ ] **Step 1: Rewrite main.py**

Replace **entire** content of `services/accounting-service/app/main.py` with:

```python
from shared_lib import create_app

from .database import engine, Base, get_db
from .routers import transactions, cards, recurring, categories, payment_methods

# Create tables (will be replaced by Alembic in Plan 3)
Base.metadata.create_all(bind=engine)

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

- [ ] **Step 2: Delete now-unused files**

```bash
rm services/accounting-service/app/tracing.py
rm services/accounting-service/app/routers/health.py  # created in Plan 1, now in shared-lib
```

If `routers/health.py` doesn't exist yet (Plan 1 not merged), skip the second `rm`.

- [ ] **Step 3: Remove `load_dotenv` from main.py**

Confirm the new `main.py` does NOT call `load_dotenv` — `SharedSettings` handles env loading via `pydantic-settings`.

Note: `database.py` still calls `get_database_url()` from shared_lib which uses `load_dotenv` internally. This is fine — database.py is imported before `create_app` runs, so env vars are loaded in time. No change needed to `database.py` in this plan.

- [ ] **Step 4: Run existing tests to verify no regression**

```bash
cd services/accounting-service
pytest -v
```

Expected: all existing tests pass. The test fixtures use SQLite in-memory so they're unaffected by the factory change.

- [ ] **Step 5: Manual smoke test**

```bash
cd services/accounting-service
uvicorn app.main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/health | python -m json.tool
curl -s http://localhost:8000/docs | head -5
kill %1
```

Expected: `/health` returns `{"status": "ok"}`, `/docs` returns HTML.

- [ ] **Step 6: Commit**

```bash
git add services/accounting-service/app/main.py
git rm services/accounting-service/app/tracing.py 2>/dev/null; true
git rm services/accounting-service/app/routers/health.py 2>/dev/null; true
git commit -m "refactor(accounting): use shared create_app() factory, remove local boilerplate"
```

---

### Task 7: Migrate stock-portfolio-service to use factory

**Files:**
- Modify: `services/stock-portfolio-service/app/main.py`
- Delete: `services/stock-portfolio-service/app/tracing.py`
- Delete: `services/stock-portfolio-service/app/routers/health.py` (from Plan 1)

- [ ] **Step 1: Rewrite main.py**

Replace **entire** content of `services/stock-portfolio-service/app/main.py` with:

```python
from shared_lib import create_app

from .database import engine, Base, get_db
from .routers import portfolio

# Create tables (will be replaced by Alembic in Plan 3)
Base.metadata.create_all(bind=engine)

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

- [ ] **Step 2: Delete unused files**

```bash
rm services/stock-portfolio-service/app/tracing.py
rm services/stock-portfolio-service/app/routers/health.py 2>/dev/null; true
```

- [ ] **Step 3: Run tests**

```bash
cd services/stock-portfolio-service
pytest -v
```

Expected: all pass.

- [ ] **Step 4: Manual smoke test**

```bash
uvicorn app.main:app --port 8001 &
sleep 3
curl -s http://localhost:8001/health | python -m json.tool
kill %1
```

- [ ] **Step 5: Commit**

```bash
git add services/stock-portfolio-service/app/main.py
git rm services/stock-portfolio-service/app/tracing.py 2>/dev/null; true
git rm services/stock-portfolio-service/app/routers/health.py 2>/dev/null; true
git commit -m "refactor(stock): use shared create_app() factory, remove local boilerplate"
```

---

### Task 8: Update accounting-service conftest to provide `client` fixture

The existing `conftest.py` only provides `db_session`, not a FastAPI `TestClient`. Health tests from Plan 1 (and future tests) need a `client` fixture. If Plan 1 already added one, skip this task.

**Files:**
- Modify: `services/accounting-service/tests/conftest.py`

- [ ] **Step 1: Check if `client` fixture already exists**

```bash
grep -n "def client" services/accounting-service/tests/conftest.py
```

If it prints a match, skip the rest of this task.

- [ ] **Step 2: Add `client` fixture**

Append to `services/accounting-service/tests/conftest.py`:

```python
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 3: Do the same for stock-portfolio-service**

Check and append the same pattern to `services/stock-portfolio-service/tests/conftest.py`, changing imports to use `from app.main import app` and `from app.database import get_db`.

- [ ] **Step 4: Run full test suites**

```bash
cd services/accounting-service && pytest -v
cd ../stock-portfolio-service && pytest -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add services/accounting-service/tests/conftest.py \
        services/stock-portfolio-service/tests/conftest.py
git commit -m "test: add client fixture with DB override to both Python services"
```

---

## Self-Review Checklist

- [ ] `SharedSettings` loads from root `.env` without hardcoded relative paths
- [ ] Error responses always include `code`, `message`, `trace_id` (same shape Java's `GlobalExceptionHandler` returns)
- [ ] `create_app()` calls `setup_tracing()` AFTER all routers are registered
- [ ] Both services' `main.py` are under 20 lines — no CORS / tracing / error handler boilerplate
- [ ] No circular imports (app_factory imports tracing, errors, health — none of them import app_factory)
- [ ] `database.py` in each service is unchanged (per-service pool tuning is intentional)
- [ ] All existing tests still pass after migration

## Out of Scope

- Migrating `database.py` duplication into shared-lib (pool configs differ intentionally)
- Removing `Base.metadata.create_all` (done in Plan 3: Alembic)
- Changing endpoint behaviour or response schemas
