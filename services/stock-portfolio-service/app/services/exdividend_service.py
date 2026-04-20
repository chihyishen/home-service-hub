import logging
import requests
from datetime import date
from typing import List, Optional, Set

from ..schemas.portfolio import ExDividendRecord

logger = logging.getLogger(__name__)

TWSE_EXDIVIDEND_URL = "https://openapi.twse.com.tw/v1/exchangeReport/TWT48U"


def roc_to_date(roc_str: str) -> Optional[date]:
    """
    Convert ROC date string "114/06/15" to Python date(2025, 6, 15).
    ROC year + 1911 = Gregorian year.
    """
    if not roc_str or roc_str.strip() in ("", "-"):
        return None
    try:
        parts = roc_str.strip().split("/")
        if len(parts) != 3:
            return None
        year = int(parts[0]) + 1911
        month = int(parts[1])
        day = int(parts[2])
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def parse_twse_exdividend_records(
    raw_records: list, held_symbols: Set[str]
) -> List[ExDividendRecord]:
    """
    Parse a list of raw TWSE API dicts into ExDividendRecord objects,
    keeping only records for symbols in held_symbols.
    Skips records with no valid ex-dividend or ex-rights date.
    """
    results = []
    for item in raw_records:
        symbol = item.get("股票代號", "").strip()
        if symbol not in held_symbols:
            continue

        ex_div_date = roc_to_date(item.get("除息交易日", ""))
        ex_rights_date = roc_to_date(item.get("除權交易日", ""))

        if ex_div_date is None and ex_rights_date is None:
            continue

        results.append(
            ExDividendRecord(
                symbol=symbol,
                name=item.get("名稱", symbol),
                ex_dividend_date=ex_div_date,
                ex_rights_date=ex_rights_date,
                cash_dividend=item.get("最近一次配息") or None,
                stock_dividend=item.get("最近一次配股") or None,
            )
        )

    def _sort_key(r: ExDividendRecord):
        d = r.ex_dividend_date or r.ex_rights_date
        return d if d else date(9999, 12, 31)

    results.sort(key=_sort_key)
    return results


def fetch_upcoming_exdividends(held_symbols: Set[str]) -> List[ExDividendRecord]:
    """
    Fetch the TWSE upcoming ex-dividend table and return records for held_symbols only.
    """
    if not held_symbols:
        return []
    try:
        resp = requests.get(TWSE_EXDIVIDEND_URL, timeout=10, verify=False)
        resp.raise_for_status()
        raw = resp.json()
        if not isinstance(raw, list):
            logger.warning("TWSE ex-dividend API returned unexpected format")
            return []
        return parse_twse_exdividend_records(raw, held_symbols)
    except Exception as e:
        logger.error(f"Failed to fetch TWSE ex-dividend data: {e}")
        return []
