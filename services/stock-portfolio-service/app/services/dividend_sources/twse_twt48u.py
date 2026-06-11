"""TWSE TWT48U_ALL OpenAPI (current ex-dividend / ex-rights snapshot).

TWSE migrated this dataset from ``/exchangeReport/TWT48U`` (which now 404s)
to ``/exchangeReport/TWT48U_ALL``. The new payload uses English keys and
7-digit ROC dates with no separators (e.g. ``"1150602"`` == ROC 115/06/02
== 2026-06-02). Both ex-dividend (息) and ex-rights (權) events are returned
here, so the retired TWT49U endpoint is no longer needed.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from ..twse_client import get_twse_client
from . import DividendEventRow

logger = logging.getLogger(__name__)

URL = "https://openapi.twse.com.tw/v1/exchangeReport/TWT48U_ALL"
SOURCE = "TWSE_TWT48U"


def _roc_to_date(roc_str: object):
    """Parse a 7-digit (or 6-digit) ROC date string like ``1150602``."""
    if roc_str is None:
        return None
    from datetime import date as dt_date

    text = str(roc_str).strip()
    if not text or text == "-" or not text.isdigit() or len(text) < 5:
        return None
    try:
        year = int(text[:-4]) + 1911
        month = int(text[-4:-2])
        day = int(text[-2:])
        return dt_date(year, month, day)
    except (ValueError, IndexError):
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "0", "0.0", "0.00"}:
        return None
    try:
        result = Decimal(text)
    except InvalidOperation:
        return None
    return result if result != 0 else None


def _coerce_list(raw: bytes | str | dict | list) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, (bytes, str)):
        try:
            parsed = json.loads(raw.decode("utf-8-sig") if isinstance(raw, bytes) else raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return []
        return parsed if isinstance(parsed, list) else []
    return []


def parse_twt48u(raw: bytes | str | list[dict[str, Any]]) -> list[DividendEventRow]:
    rows: list[DividendEventRow] = []
    for item in _coerce_list(raw):
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("Code", "")).strip()
        if not symbol:
            continue
        event_date = _roc_to_date(item.get("Date"))
        if event_date is None:
            continue
        rows.append(
            DividendEventRow(
                symbol=symbol,
                ex_dividend_date=event_date,
                cash_dividend=_decimal_or_none(item.get("CashDividend")),
                stock_dividend=_decimal_or_none(item.get("StockDividendRatio")),
                source=SOURCE,
            )
        )
    return rows


def fetch_twt48u(year: int | None = None) -> list[DividendEventRow]:
    """TWT48U_ALL has no year filter — returns the current snapshot regardless."""
    try:
        raw = get_twse_client().fetch_exdividend_json(URL)
    except Exception as exc:
        logger.error("Failed to fetch TWT48U_ALL: %s", exc)
        return []
    if not raw:
        # TWT48U_ALL returns the whole market on any business day; an empty
        # payload means the endpoint changed or broke (as TWT48U did). Emit a
        # loud signal so monitoring catches it instead of silently going blank.
        logger.warning(
            "twse_twt48u.empty_snapshot — TWT48U_ALL returned no rows; "
            "the upstream OpenAPI endpoint (%s) may have changed",
            URL,
        )
        return []
    return parse_twt48u(raw)
