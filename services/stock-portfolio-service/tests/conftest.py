import os

os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("SYMBOL_HISTORY_AUTOBACKFILL", "false")
# ponytail: tests never trace; drop the endpoint so setup_tracing no-ops and no
# live OTLP daemon thread races a closed stderr at shutdown (SIGABRT/exit 134).
os.environ.pop("OTEL_COLLECTOR_ENDPOINT_GRPC", None)

import pytest
from app.database import Base, get_db
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # NOTE: Tests use create_all() instead of Alembic for speed.
    # Prod uses Alembic migrations only (see alembic/ directory).
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
