"""Per-symbol TWSE history backfill (STOCK_DAY).

When a brand-new symbol is first transacted, its price history must be
fetched for the dates it was held — but the full-market daily backfill
skips dates already covered by other symbols, so a new symbol would miss
all historical prices. STOCK_DAY returns one month of OHLC for a single
symbol, which is both correct and cheap (~1 request/month).
"""

import json
from datetime import date
from decimal import Decimal

from app.services import symbol_history_service as shs


def _stock_day(*rows) -> dict:
    return {
        "stat": "OK",
        "fields": [
            "日期", "成交股數", "成交金額", "開盤價", "最高價",
            "最低價", "收盤價", "漲跌價差", "成交筆數", "註記",
        ],
        "data": list(rows),
    }


def test_parse_stock_day_basic():
    payload = _stock_day(
        ["115/06/01", "135,817,122", "14,329,024,058", "105.25", "106.70",
         "104.50", "105.50", "+0.10", "156,361", ""],
    )
    rows = shs.parse_stock_day("0050", payload)
    assert len(rows) == 1
    r = rows[0]
    assert r.symbol == "0050"
    assert r.date == date(2026, 6, 1)
    assert r.open == Decimal("105.25")
    assert r.high == Decimal("106.70")
    assert r.low == Decimal("104.50")
    assert r.close == Decimal("105.50")
    assert r.volume == 135817122
    assert r.turnover == Decimal("14329024058")
    assert r.source == "TWSE"


def test_parse_stock_day_skips_no_trade_rows():
    payload = _stock_day(
        ["115/06/02", "0", "0", "--", "--", "--", "--", "0.00", "0", ""],
    )
    assert shs.parse_stock_day("0050", payload) == []


def test_parse_stock_day_accepts_bytes():
    """market_data_service._http_get returns raw bytes, so the parser must
    decode JSON itself (regression: it previously only accepted dicts and
    silently returned [] for every live fetch)."""
    raw = json.dumps(_stock_day(
        ["115/06/01", "1,000", "10,500", "10.00", "11.00", "9.00", "10.50", "+0.1", "5", ""],
    )).encode("utf-8")
    rows = shs.parse_stock_day("0050", raw)
    assert len(rows) == 1
    assert rows[0].close == Decimal("10.50")


def test_parse_stock_day_non_ok_stat_returns_empty():
    assert shs.parse_stock_day("9999", {"stat": "很抱歉，沒有符合條件的資料!"}) == []


def test_parse_stock_day_empty_payload():
    assert shs.parse_stock_day("0050", {}) == []


def test_months_in_range_spans_boundaries():
    months = shs.months_in_range(date(2025, 11, 10), date(2026, 2, 3))
    assert months == [(2025, 11), (2025, 12), (2026, 1), (2026, 2)]


def test_months_in_range_single_month():
    assert shs.months_in_range(date(2026, 6, 1), date(2026, 6, 30)) == [(2026, 6)]
