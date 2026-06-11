"""Per-symbol price-history backfill via TWSE STOCK_DAY.

The full-market daily backfill (``market_data_service.backfill_date`` /
``networth_backfill_service``) skips dates already present in
``price_history``. That is correct for the daily cron, but means a *newly
held* symbol never gets prices for dates other symbols already covered.

STOCK_DAY returns one month of OHLC for a single symbol, so backfilling a
new symbol's holding range costs ~1 request/month and never disturbs other
rows.

Limitation: STOCK_DAY is TWSE (上市) only. For TPEx (上櫃) symbols the fetch
returns nothing and we log a warning — those still need a manual full-market
backfill. See the handoff notes.
"""

from __future__ import annotations

import json
import logging
from datetime import date as dt_date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from . import market_data_service
from .market_data_service import DailyPriceRow

logger = logging.getLogger(__name__)

STOCK_DAY_URL = "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
SOURCE = "TWSE"


def _roc_to_date(value: object) -> dt_date | None:
    parts = str(value).strip().split("/")
    if len(parts) != 3:
        return None
    try:
        return dt_date(int(parts[0]) + 1911, int(parts[1]), int(parts[2]))
    except ValueError:
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    text = str(value).strip().replace(",", "")
    if not text or text in {"--", "-", "X0.00"}:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _int_or_none(value: Any) -> int | None:
    text = str(value).strip().replace(",", "")
    return int(text) if text.isdigit() else None


def parse_stock_day(symbol: str, payload: Any) -> list[DailyPriceRow]:
    """Parse a TWSE STOCK_DAY monthly payload for one symbol.

    Accepts the raw ``bytes``/``str`` returned by ``_http_get`` as well as an
    already-decoded ``dict``.
    """
    if isinstance(payload, (bytes, str)):
        try:
            payload = json.loads(
                payload.decode("utf-8-sig") if isinstance(payload, bytes) else payload
            )
        except (UnicodeDecodeError, json.JSONDecodeError):
            return []
    if not isinstance(payload, dict) or payload.get("stat") != "OK":
        return []
    rows: list[DailyPriceRow] = []
    for item in payload.get("data") or []:
        if not isinstance(item, (list, tuple)) or len(item) < 7:
            continue
        day = _roc_to_date(item[0])
        close = _decimal_or_none(item[6])
        if day is None or close is None:  # close == "--" on no-trade days
            continue
        rows.append(
            DailyPriceRow(
                symbol=symbol,
                date=day,
                open=_decimal_or_none(item[3]),
                high=_decimal_or_none(item[4]),
                low=_decimal_or_none(item[5]),
                close=close,
                volume=_int_or_none(item[1]),
                turnover=_decimal_or_none(item[2]),
                source=SOURCE,
            )
        )
    return rows


def months_in_range(from_date: dt_date, to_date: dt_date) -> list[tuple[int, int]]:
    """Inclusive list of (year, month) covering ``[from_date, to_date]``."""
    out: list[tuple[int, int]] = []
    year, month = from_date.year, from_date.month
    while (year, month) <= (to_date.year, to_date.month):
        out.append((year, month))
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return out


def fetch_twse_symbol_month(symbol: str, year: int, month: int) -> list[DailyPriceRow]:
    payload = market_data_service._http_get(
        STOCK_DAY_URL,
        {"response": "json", "date": f"{year}{month:02d}01", "stockNo": symbol},
    )
    if not payload:
        return []
    return parse_stock_day(symbol, payload)


def backfill_symbol_history(
    db: Session, symbol: str, from_date: dt_date, to_date: dt_date
) -> int:
    """Fetch + persist one symbol's OHLC across ``[from_date, to_date]``.

    Returns the number of rows written. Logs a warning (and writes nothing)
    when TWSE has no data for the symbol — typically a TPEx/上櫃 listing.
    """
    collected: list[DailyPriceRow] = []
    for year, month in months_in_range(from_date, to_date):
        collected.extend(fetch_twse_symbol_month(symbol, year, month))
    kept = [r for r in collected if from_date <= r.date <= to_date]
    if not kept:
        logger.warning(
            "symbol_history.no_twse_data — no TWSE STOCK_DAY rows for %s in "
            "[%s, %s]; likely a TPEx/上櫃 listing. Run a manual full-market "
            "backfill for this symbol's range.",
            symbol,
            from_date.isoformat(),
            to_date.isoformat(),
        )
        return 0
    return market_data_service.upsert_rows(db, kept)
