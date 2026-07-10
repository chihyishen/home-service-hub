from types import SimpleNamespace

from app import schemas
from app.routers import transactions


class _Span:
    def __init__(self):
        self.attributes = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def set_attribute(self, key, value):
        self.attributes[key] = value


class _Tracer:
    def __init__(self):
        self.span = _Span()

    def start_as_current_span(self, _name):
        return self.span


def test_transaction_router_spans_do_not_capture_sensitive_bodies(monkeypatch):
    tracer = _Tracer()
    monkeypatch.setattr(transactions, "tracer", tracer)
    monkeypatch.setattr(
        transactions.transaction_service,
        "create_transaction",
        lambda _db, _transaction: SimpleNamespace(id=42),
    )

    transactions.create_transaction(
        schemas.TransactionCreate(
            category_id=7,
            item="secret item",
            paid_amount=1234,
            transaction_amount=1234,
            payment_method="secret method",
            card_id=9,
            note="secret note",
            tags=["secret tag"],
        ),
        db=None,
    )

    assert tracer.span.attributes == {
        "transaction.type": "EXPENSE",
        "transaction.category_id": 7,
        "transaction.card_id": 9,
        "transaction.id": 42,
    }
    assert not any("body" in key or "item" in key or "amount" in key for key in tracer.span.attributes)
