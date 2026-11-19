import os

os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("SYMBOL_HISTORY_AUTOBACKFILL", "false")
os.environ.setdefault("POST_IMPORT_RECALC_ENABLED", "false")

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


class _FakeAccounting:
    """記帳服務替身：測試不打真的 HTTP，並記錄呼叫供斷言。"""

    def __init__(self):
        self.calls = []

    def _next_id(self):
        return 900 + len(self.calls)

    def create_for(self, txn, label):
        from app.services.accounting_link import amount_of
        self.calls.append(("create", label, amount_of(txn)))
        return self._next_id()

    def sync(self, txn):
        if txn.accounting_transaction_id:
            self.calls.append(("sync", txn.accounting_transaction_id))

    def create_for_dividend(self, div, name):
        from app.services.accounting_link import dividend_amount_of
        self.calls.append(("create_dividend", f"{name} 配息", dividend_amount_of(div)))
        return self._next_id()

    def sync_dividend(self, div):
        if div.accounting_transaction_id:
            self.calls.append(("sync_dividend", div.accounting_transaction_id))

    def remove(self, accounting_id):
        if accounting_id:
            self.calls.append(("remove", accounting_id))


@pytest.fixture(autouse=True)
def fake_accounting(monkeypatch):
    from app.services import accounting_link

    fake = _FakeAccounting()
    for name in ("create_for", "sync", "remove", "create_for_dividend", "sync_dividend"):
        monkeypatch.setattr(accounting_link, name, getattr(fake, name))
    return fake
