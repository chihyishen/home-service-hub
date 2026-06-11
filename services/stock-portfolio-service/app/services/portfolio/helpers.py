import os
from datetime import UTC, datetime
from datetime import date as date_type
from decimal import Decimal


def sanitize_symbol(symbol: str) -> str:
    """
    清理股票代碼：移除 .TW, .TWO (不分大小寫) 並轉為大寫，只保留前面的代碼。
    例如: 0050.TW -> 0050
    """
    if not symbol:
        return ""
    return symbol.split('.')[0].upper().strip()


def _escape_like_prefix(value: str) -> str:
    """Escape SQL LIKE wildcards so user input is matched literally.

    Without this, a ``%`` or ``_`` in the input would silently turn into
    wildcards in the ILIKE pattern. Backslash is escaped first so it
    cannot consume the escapes added afterwards.
    """
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _resolve_sort_trade_date(
    trade_date: datetime,
) -> datetime:
    if trade_date.tzinfo is None:
        return trade_date
    return trade_date.astimezone(UTC).replace(tzinfo=None)


def _trade_calendar_date(trade_date: datetime) -> date_type:
    """Calendar date used for day-trade bucketing.

    Normalises to UTC date (matches ``_resolve_sort_trade_date``). TW trading
    hours run 01:00-05:30 UTC, so the UTC date matches the TW market date.
    """

    return _resolve_sort_trade_date(trade_date).date()


def _is_odd_lot(quantity: int) -> bool:
    return quantity < 1000 or quantity % 1000 != 0


def _env_decimal(name: str, default: str) -> Decimal:
    val = os.getenv(name)
    if not val:
        return Decimal(default)
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal(default)
