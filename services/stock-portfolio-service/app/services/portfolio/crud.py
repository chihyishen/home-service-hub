from datetime import UTC, datetime, timedelta
from datetime import date as date_type

from sqlalchemy import Column, func
from sqlalchemy.orm import Session

from ...models import portfolio as models
from ...schemas import portfolio as schemas
from .. import symbol_map_service
from .day_trade import _recompute_day_trade_flags, _validate_transaction_ledger
from .helpers import _escape_like_prefix, _trade_calendar_date, sanitize_symbol
from .history_backfill import (
    _schedule_symbol_history_backfill,
    _schedule_tpex_symbol_history_backfill,
    _symbol_uses_tpex_history,
)

_ONE_DAY = timedelta(days=1)


def create_transaction(db: Session, transaction: schemas.TransactionCreate):
    # Task 2: 清理 symbol
    transaction_data = transaction.model_dump()
    transaction_data["symbol"] = sanitize_symbol(transaction_data["symbol"])
    transaction_data["trade_date"] = transaction_data.get("trade_date") or datetime.now(UTC)
    transaction_data["instrument_type"] = symbol_map_service.lookup_warrant_type(
        db, transaction_data["symbol"]
    )

    _validate_transaction_ledger(db, transaction_data)

    # A symbol with no prior transaction is new to the portfolio; its price
    # history must be backfilled separately (the full-market cron skips dates
    # already covered by other symbols).
    is_new_symbol = (
        db.query(models.Transaction.id)
        .filter(models.Transaction.symbol == transaction_data["symbol"])
        .first()
        is None
    )

    db_transaction = models.Transaction(**transaction_data)
    db.add(db_transaction)
    db.flush()
    _recompute_day_trade_flags(
        db,
        db_transaction.symbol,
        _trade_calendar_date(db_transaction.trade_date),
    )
    db.commit()
    db.refresh(db_transaction)

    if is_new_symbol:
        trade_day = _trade_calendar_date(db_transaction.trade_date)
        if _symbol_uses_tpex_history(db, db_transaction.symbol):
            _schedule_tpex_symbol_history_backfill(db_transaction.symbol, trade_day)
        else:
            _schedule_symbol_history_backfill(db_transaction.symbol, trade_day)
    return db_transaction

def create_dividend(db: Session, dividend: schemas.DividendCreate):
    # Task 2: 清理 symbol
    dividend_data = dividend.model_dump()
    dividend_data["symbol"] = sanitize_symbol(dividend_data["symbol"])

    db_dividend = models.Dividend(**dividend_data)
    db.add(db_dividend)
    db.commit()
    db.refresh(db_dividend)
    return db_dividend


_TRANSACTION_SORT_FIELDS: dict[str, Column] = {
    "trade_date": models.Transaction.trade_date,
    "symbol": models.Transaction.symbol,
    "type": models.Transaction.type,
    "price": models.Transaction.price,
    "quantity": models.Transaction.quantity,
}

_DIVIDEND_SORT_FIELDS: dict[str, Column] = {
    "ex_dividend_date": models.Dividend.ex_dividend_date,
    "symbol": models.Dividend.symbol,
    "amount": models.Dividend.amount,
    "source": models.Dividend.source,
}


def _parse_sort(value: str, allowlist: dict[str, Column]) -> tuple[str, str]:
    """Split ``"field:direction"`` and validate against ``allowlist``.

    Raises ``ValueError`` on bad syntax or unknown field. Caller maps that
    to HTTP 422.
    """
    if not value or ":" not in value:
        raise ValueError(f"sort must be '<field>:<asc|desc>', got '{value}'")
    field, _, direction = value.partition(":")
    field = field.strip()
    direction = direction.strip().lower()
    if direction not in ("asc", "desc"):
        raise ValueError(f"sort direction must be 'asc' or 'desc', got '{direction}'")
    if field not in allowlist:
        raise ValueError(f"sort field '{field}' not allowed; choose one of {sorted(allowlist)}")
    return field, direction


def list_transactions(
    db: Session,
    *,
    symbol: str | None = None,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    side: str | None = None,
    sort_field: str = "trade_date",
    sort_dir: str = "desc",
    offset: int = 0,
    limit: int = 25,
) -> tuple[list[models.Transaction], int]:
    """Return ``(items, total)`` paged + filtered transactions.

    ``date_from`` / ``date_to`` are inclusive bounds on ``trade_date``.
    ``id desc`` is always appended as tie-breaker so pages stay stable.
    """
    if sort_field not in _TRANSACTION_SORT_FIELDS:
        raise ValueError(f"sort field '{sort_field}' not allowed")

    base = db.query(models.Transaction)
    if symbol:
        # Prefix match so typing "0" shows every 0xxx ETF, "00" narrows to
        # 00xxx, etc. Sanitize first to keep casing/whitespace consistent;
        # only apply the filter if a non-empty stem remains so a
        # whitespace-only input does not degenerate into ILIKE '%' and
        # silently bypass filtering.
        stem = sanitize_symbol(symbol)
        if stem:
            base = base.filter(
                models.Transaction.symbol.ilike(
                    f"{_escape_like_prefix(stem)}%", escape="\\"
                )
            )
    if date_from is not None:
        base = base.filter(
            models.Transaction.trade_date
            >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        )
    if date_to is not None:
        # date_to inclusive — use < (next day midnight)
        end_exclusive = (
            datetime.combine(date_to, datetime.min.time(), tzinfo=UTC) + _ONE_DAY
        )
        base = base.filter(models.Transaction.trade_date < end_exclusive)
    if side:
        base = base.filter(models.Transaction.type == side)

    total = base.with_entities(func.count(models.Transaction.id)).scalar() or 0

    sort_col = _TRANSACTION_SORT_FIELDS[sort_field]
    order = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    rows = (
        base.order_by(order, models.Transaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, int(total)

def update_transaction(db: Session, transaction_id: int, transaction_update: schemas.TransactionCreate):
    db_transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_transaction:
        return None

    old_symbol = sanitize_symbol(db_transaction.symbol)
    old_calendar = _trade_calendar_date(db_transaction.trade_date)

    update_data = transaction_update.model_dump(exclude_unset=True)
    update_data["symbol"] = sanitize_symbol(update_data["symbol"])
    if "trade_date" in update_data:
        update_data["trade_date"] = update_data["trade_date"] or db_transaction.trade_date
    else:
        update_data["trade_date"] = db_transaction.trade_date

    if update_data["symbol"] != old_symbol or db_transaction.instrument_type is None:
        update_data["instrument_type"] = symbol_map_service.lookup_warrant_type(
            db, update_data["symbol"]
        )

    _validate_transaction_ledger(db, update_data, existing_transaction=db_transaction)

    for key, value in update_data.items():
        setattr(db_transaction, key, value)

    db.flush()

    new_symbol = sanitize_symbol(db_transaction.symbol)
    new_calendar = _trade_calendar_date(db_transaction.trade_date)
    _recompute_day_trade_flags(db, old_symbol, old_calendar)
    if (new_symbol, new_calendar) != (old_symbol, old_calendar):
        _recompute_day_trade_flags(db, new_symbol, new_calendar)

    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def delete_transaction(db: Session, transaction_id: int):
    db_transaction = db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()
    if not db_transaction:
        return False

    symbol = sanitize_symbol(db_transaction.symbol)
    calendar = _trade_calendar_date(db_transaction.trade_date)

    db.delete(db_transaction)
    db.flush()
    _recompute_day_trade_flags(db, symbol, calendar)
    db.commit()
    return True


def list_dividends(
    db: Session,
    *,
    symbol: str | None = None,
    date_from: date_type | None = None,
    date_to: date_type | None = None,
    source: str | None = None,
    sort_field: str = "ex_dividend_date",
    sort_dir: str = "desc",
    offset: int = 0,
    limit: int = 25,
) -> tuple[list[models.Dividend], int]:
    """Return ``(items, total)`` paged + filtered dividends."""
    if sort_field not in _DIVIDEND_SORT_FIELDS:
        raise ValueError(f"sort field '{sort_field}' not allowed")

    base = db.query(models.Dividend)
    if symbol:
        # Prefix match — same UX as transactions list.
        stem = sanitize_symbol(symbol)
        if stem:
            base = base.filter(
                models.Dividend.symbol.ilike(
                    f"{_escape_like_prefix(stem)}%", escape="\\"
                )
            )
    if date_from is not None:
        base = base.filter(
            models.Dividend.ex_dividend_date
            >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC)
        )
    if date_to is not None:
        end_exclusive = (
            datetime.combine(date_to, datetime.min.time(), tzinfo=UTC) + _ONE_DAY
        )
        base = base.filter(models.Dividend.ex_dividend_date < end_exclusive)
    if source is not None:
        base = base.filter(models.Dividend.source == source)

    total = base.with_entities(func.count(models.Dividend.id)).scalar() or 0

    sort_col = _DIVIDEND_SORT_FIELDS[sort_field]
    order = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    rows = (
        base.order_by(order, models.Dividend.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, int(total)

def update_dividend(db: Session, dividend_id: int, dividend_update: schemas.DividendCreate):
    db_dividend = db.query(models.Dividend).filter(models.Dividend.id == dividend_id).first()
    if not db_dividend:
        return None
    
    update_data = dividend_update.model_dump(exclude_unset=True)
    update_data["symbol"] = sanitize_symbol(update_data["symbol"])
    
    for key, value in update_data.items():
        setattr(db_dividend, key, value)
    
    db.commit()
    db.refresh(db_dividend)
    return db_dividend

def delete_dividend(db: Session, dividend_id: int):
    db_dividend = db.query(models.Dividend).filter(models.Dividend.id == dividend_id).first()
    if not db_dividend:
        return False
    db.delete(db_dividend)
    db.commit()
    return True
