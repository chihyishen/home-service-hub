"""price_history must only ever store symbols the user has held.

Storing the full TWSE/TPEx universe (~7000 symbols/day) was pure waste —
only held symbols are read (by the chart endpoint and the snapshot
backfill). These tests pin the two pieces that keep the table lean:

- ``portfolio_service.get_ever_held_symbols`` — the symbol allow-list.
- ``market_data_service.filter_rows_to_symbols`` — drops everything else
  before persistence.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from app.schemas import portfolio as schemas
from app.services import market_data_service as mds
from app.services import portfolio_service as svc


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


def _row(symbol: str) -> mds.DailyPriceRow:
    return mds.DailyPriceRow(
        symbol=symbol,
        date=date(2026, 6, 4),
        open=Decimal("10"),
        high=Decimal("11"),
        low=Decimal("9"),
        close=Decimal("10.5"),
        volume=1000,
        turnover=Decimal("10500"),
        source="TWSE",
    )


def test_get_ever_held_symbols_includes_all_transacted(db_session):
    svc.create_transaction(
        db_session, _buy("0050", datetime(2025, 11, 10, 1, 30, tzinfo=timezone.utc))
    )
    svc.create_transaction(
        db_session, _buy("00919", datetime(2026, 2, 3, 1, 30, tzinfo=timezone.utc))
    )
    assert svc.get_ever_held_symbols(db_session) == {"0050", "00919"}


def test_get_ever_held_symbols_keeps_sold_out_positions(db_session):
    """A fully-sold position is still 'ever held' — its chart history stays."""
    day = datetime(2025, 11, 10, 1, 30, tzinfo=timezone.utc)
    svc.create_transaction(db_session, _buy("2330", day))
    svc.create_transaction(
        db_session,
        schemas.TransactionCreate(
            symbol="2330",
            type=schemas.TransactionType("SELL"),
            quantity=1000,
            price=Decimal("12.00"),
            trade_date=datetime(2026, 1, 5, 1, 30, tzinfo=timezone.utc),
            fee=Decimal("0.00"),
            tax=Decimal("0.00"),
        ),
    )
    assert "2330" in svc.get_ever_held_symbols(db_session)


def test_filter_rows_to_symbols_drops_unheld():
    rows = [_row("0050"), _row("2317"), _row("00919")]
    kept = mds.filter_rows_to_symbols(rows, {"0050", "00919"})
    assert {r.symbol for r in kept} == {"0050", "00919"}


def test_filter_rows_to_symbols_empty_allowlist_keeps_nothing():
    assert mds.filter_rows_to_symbols([_row("0050")], set()) == []
