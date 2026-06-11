from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from sqlalchemy.orm import Session

from ...models import portfolio as models
from .. import symbol_map_service
from .helpers import _is_odd_lot, _resolve_sort_trade_date, _trade_calendar_date, sanitize_symbol

_ONE_DAY = timedelta(days=1)


def _recompute_day_trade_flags(
    db: Session, symbol: str, calendar_date: date_type
) -> None:
    """Flip ``is_day_trade`` for every transaction in the (symbol, date) bucket.

    A transaction is a day-trade when the same symbol has BOTH a BUY and a
    SELL on the same calendar trade date. All rows in the bucket share the
    same flag; recompute and persist in-place. Caller commits.
    """

    normalized = sanitize_symbol(symbol)
    day_start = datetime.combine(calendar_date, datetime.min.time(), tzinfo=UTC)
    day_end = day_start + _ONE_DAY
    rows = (
        db.query(models.Transaction)
        .filter(models.Transaction.symbol == normalized)
        .filter(models.Transaction.trade_date >= day_start)
        .filter(models.Transaction.trade_date < day_end)
        .all()
    )
    # _trade_calendar_date normalises to UTC date; rows already bounded above.
    bucket = [
        row for row in rows
        if _trade_calendar_date(row.trade_date) == calendar_date
    ]
    board_lot = [row for row in bucket if not _is_odd_lot(row.quantity)]
    has_buy = any(row.type == models.TransactionType.BUY for row in board_lot)
    has_sell = any(row.type == models.TransactionType.SELL for row in board_lot)
    marker_present = any(
        getattr(row, "broker_day_trade_marker", None) in {"沖買", "沖賣"}
        for row in board_lot
    )
    if marker_present:
        board_flag = all(
            symbol_map_service.is_day_trade_eligible(
                db, normalized, getattr(row, "instrument_type", None)
            )
            for row in board_lot
        )
    elif has_buy and has_sell:
        board_flag = all(
            symbol_map_service.is_day_trade_eligible(
                db, normalized, getattr(row, "instrument_type", None)
            )
            for row in board_lot
        )
    else:
        board_flag = False
    for row in bucket:
        new_flag = False if _is_odd_lot(row.quantity) else board_flag
        if row.is_day_trade != new_flag:
            row.is_day_trade = new_flag


def _validate_symbol_ledger(symbol: str, ledger_entries: list[dict[str, object]]) -> None:
    long_qty = 0
    short_qty = 0

    for entry in sorted(
        ledger_entries,
        key=lambda item: (item["sort_trade_date"], item["sort_id"]),
    ):
        quantity = int(entry["quantity"])
        side = entry.get("position_side", models.PositionSide.LONG)
        if not isinstance(side, models.PositionSide):
            side = models.PositionSide(side)
        is_buy = entry["type"] == models.TransactionType.BUY

        if side is models.PositionSide.LONG and is_buy:
            long_qty += quantity
            continue
        if side is models.PositionSide.SHORT and not is_buy:
            short_qty += quantity
            continue

        if side is models.PositionSide.LONG:
            available = long_qty
            long_qty -= quantity
            if long_qty >= 0:
                continue
            if available <= 0:
                raise ValueError(
                    f"Cannot sell {quantity} shares of {symbol} without holdings"
                )
            raise ValueError(
                f"Cannot sell {quantity} shares of {symbol}; only {available} available"
            )

        available = short_qty
        short_qty -= quantity
        if short_qty >= 0:
            continue
        if available <= 0:
            raise ValueError(
                f"Cannot cover {quantity} shares of {symbol} without open short"
            )
        raise ValueError(
            f"Cannot cover {quantity} shares of {symbol}; only {available} open short"
        )


def _validate_transaction_ledger(
    db: Session,
    transaction_data: dict[str, object],
    existing_transaction: models.Transaction | None = None,
) -> None:
    proposed_symbol = sanitize_symbol(str(transaction_data["symbol"]))
    symbols_to_validate = {proposed_symbol}
    if existing_transaction is not None:
        symbols_to_validate.add(sanitize_symbol(existing_transaction.symbol))

    ledger_map: dict[str, list[dict[str, object]]] = {symbol: [] for symbol in symbols_to_validate}
    persisted_transactions = (
        db.query(models.Transaction)
        .order_by(models.Transaction.trade_date, models.Transaction.id)
        .all()
    )

    for transaction in persisted_transactions:
        if existing_transaction is not None and transaction.id == existing_transaction.id:
            continue

        symbol = sanitize_symbol(transaction.symbol)
        if symbol not in symbols_to_validate:
            continue

        ledger_map[symbol].append(
            {
                "sort_trade_date": _resolve_sort_trade_date(transaction.trade_date),
                "sort_id": transaction.id,
                "type": transaction.type,
                "position_side": getattr(
                    transaction, "position_side", models.PositionSide.LONG
                ),
                "quantity": transaction.quantity,
            }
        )

    proposed_side_raw = transaction_data.get("position_side", models.PositionSide.LONG)
    proposed_side = (
        proposed_side_raw
        if isinstance(proposed_side_raw, models.PositionSide)
        else models.PositionSide(
            getattr(proposed_side_raw, "value", proposed_side_raw)
        )
    )
    ledger_map[proposed_symbol].append(
        {
            "sort_trade_date": _resolve_sort_trade_date(transaction_data["trade_date"]),
            "sort_id": existing_transaction.id if existing_transaction is not None else float("inf"),
            "type": models.TransactionType(
                getattr(transaction_data["type"], "value", transaction_data["type"])
            ),
            "position_side": proposed_side,
            "quantity": transaction_data["quantity"],
        }
    )

    for symbol, entries in ledger_map.items():
        _validate_symbol_ledger(symbol, entries)
