"""Creating the first transaction for a symbol kicks off a history backfill.

A brand-new holding has no price_history (the full-market cron skips dates
already covered by other symbols), so its chart/snapshot history would be
blank. create_transaction must trigger a per-symbol backfill the first time
a symbol is seen — and must NOT re-trigger on subsequent transactions.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.symbol_map import SymbolMap
from app.schemas import portfolio as schemas
from app.services import portfolio_service as svc

# create_transaction (now in portfolio.crud) resolves the backfill hooks from
# its own module globals, so patches must target crud, not the facade.
from app.services.portfolio import crud


def _buy(symbol: str, day: datetime) -> schemas.TransactionCreate:
    return schemas.TransactionCreate(
        symbol=symbol,
        type=schemas.TransactionType("BUY"),
        quantity=1000,
        price=Decimal("10.00"),
        trade_date=day,
        fee=Decimal("0.00"),
        tax=Decimal("0.00"),
    )


def test_first_transaction_for_symbol_triggers_backfill(db_session, monkeypatch):
    calls = []
    monkeypatch.setattr(
        crud, "_schedule_symbol_history_backfill",
        lambda symbol, from_date: calls.append((symbol, from_date)),
    )
    svc.create_transaction(
        db_session, _buy("2454", datetime(2026, 3, 2, 1, 30, tzinfo=UTC))
    )
    assert calls == [("2454", date(2026, 3, 2))]


def test_first_tpex_transaction_triggers_tpex_backfill(db_session, monkeypatch):
    db_session.add(
        SymbolMap(name="otc", symbol="5483", market="TPEX", type="上櫃股票")
    )
    db_session.commit()

    twse_calls = []
    tpex_calls = []
    monkeypatch.setattr(
        crud,
        "_schedule_symbol_history_backfill",
        lambda symbol, from_date: twse_calls.append((symbol, from_date)),
    )
    monkeypatch.setattr(
        crud,
        "_schedule_tpex_symbol_history_backfill",
        lambda symbol, from_date: tpex_calls.append((symbol, from_date)),
    )

    svc.create_transaction(
        db_session, _buy("5483", datetime(2026, 3, 2, 1, 30, tzinfo=UTC))
    )

    assert twse_calls == []
    assert tpex_calls == [("5483", date(2026, 3, 2))]


def test_second_transaction_same_symbol_does_not_retrigger(db_session, monkeypatch):
    monkeypatch.setattr(crud, "_schedule_symbol_history_backfill", lambda *a, **k: None)
    svc.create_transaction(
        db_session, _buy("2454", datetime(2026, 3, 2, 1, 30, tzinfo=UTC))
    )

    calls = []
    monkeypatch.setattr(
        crud, "_schedule_symbol_history_backfill",
        lambda symbol, from_date: calls.append((symbol, from_date)),
    )
    svc.create_transaction(
        db_session, _buy("2454", datetime(2026, 3, 5, 1, 30, tzinfo=UTC))
    )
    assert calls == []


def test_autobackfill_disabled_by_env_is_noop(monkeypatch):
    """The real scheduler hook must be a no-op when the env flag is off, so
    the test suite (and prod, if disabled) never spawns network threads."""
    monkeypatch.setenv("SYMBOL_HISTORY_AUTOBACKFILL", "false")
    # Must return without spawning a thread / touching the network.
    assert svc._schedule_symbol_history_backfill("2454", date(2026, 3, 2)) is None
    assert svc._schedule_tpex_symbol_history_backfill("5483", date(2026, 3, 2)) is None
