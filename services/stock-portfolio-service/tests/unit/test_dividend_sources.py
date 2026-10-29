"""Parser tests for the three dividend-event sources."""

import json
from datetime import date
from decimal import Decimal

from app.services.dividend_sources import tpex_otc, twse_twt48u

# ---------- TWT48U (TWT48U_ALL OpenAPI — English-keyed schema) ----------
# TWSE migrated the dataset from /exchangeReport/TWT48U (Chinese keys,
# slash-delimited ROC dates) to /exchangeReport/TWT48U_ALL: English keys
# (Code/Date/Exdividend/CashDividend/StockDividendRatio) and 7-digit ROC
# dates with no separators ("1150602" == ROC 115/06/02 == 2026-06-02).

def test_twt48u_parses_cash_dividend_event():
    payload = [
        {
            "Date": "1150602",
            "Code": "00939",
            "Name": "統一台灣高息動能",
            "Exdividend": "息",
            "CashDividend": "0.072000",
            "StockDividendRatio": "",
        }
    ]
    rows = twse_twt48u.parse_twt48u(payload)
    assert len(rows) == 1
    assert rows[0].symbol == "00939"
    assert rows[0].ex_dividend_date == date(2026, 6, 2)
    assert rows[0].cash_dividend == Decimal("0.072000")
    assert rows[0].stock_dividend is None
    assert rows[0].source == "TWSE_TWT48U"


def test_twt48u_parses_rights_event():
    payload = [
        {
            "Date": "1150611",
            "Code": "1312",
            "Name": "國喬",
            "Exdividend": "權",
            "CashDividend": "0",
            "StockDividendRatio": "0.5",
        }
    ]
    rows = twse_twt48u.parse_twt48u(payload)
    assert rows[0].symbol == "1312"
    assert rows[0].ex_dividend_date == date(2026, 6, 11)
    assert rows[0].cash_dividend is None
    assert rows[0].stock_dividend == Decimal("0.5")


def test_twt48u_skips_when_no_date():
    payload = [{"Code": "2330", "Date": "", "Exdividend": "息"}]
    assert twse_twt48u.parse_twt48u(payload) == []


def test_twt48u_skips_when_no_symbol():
    payload = [{"Code": "", "Date": "1150615", "CashDividend": "13"}]
    assert twse_twt48u.parse_twt48u(payload) == []


def test_twt48u_accepts_bytes():
    payload = json.dumps([
        {"Code": "2330", "Date": "1150615", "Exdividend": "息", "CashDividend": "13"}
    ]).encode("utf-8")
    rows = twse_twt48u.parse_twt48u(payload)
    assert len(rows) == 1
    assert rows[0].ex_dividend_date == date(2026, 6, 15)


class _FakeClient:
    def __init__(self, payload):
        self._payload = payload

    def fetch_exdividend_json(self, url):
        return self._payload


def test_twt48u_fetch_warns_when_snapshot_empty(monkeypatch, caplog):
    """TWT48U_ALL returns the whole market (~hundreds of rows) on any
    business day. An empty result means the upstream endpoint changed/broke
    again (as TWT48U -> TWT48U_ALL did), so it must emit a loud signal
    instead of silently returning []."""
    import logging

    monkeypatch.setattr(twse_twt48u, "get_twse_client", lambda: _FakeClient([]))
    with caplog.at_level(logging.WARNING):
        result = twse_twt48u.fetch_twt48u()
    assert result == []
    assert any(
        "twt48u" in r.message.lower() and "empty" in r.message.lower()
        for r in caplog.records
    ), "expected an empty-snapshot warning"


def test_twt48u_fetch_no_warning_on_normal_snapshot(monkeypatch, caplog):
    import logging

    payload = [{"Code": "00919", "Date": "1150616", "Exdividend": "息", "CashDividend": "0.6"}]
    monkeypatch.setattr(twse_twt48u, "get_twse_client", lambda: _FakeClient(payload))
    with caplog.at_level(logging.WARNING):
        rows = twse_twt48u.fetch_twt48u()
    assert len(rows) == 1
    assert not any("empty" in r.message.lower() for r in caplog.records)


# ---------- TPEx OTC ----------

def _tpex_payload(*rows):
    return {
        "tables": [
            {
                "fields": ["除權息日期", "股票代號", "x", "y", "z", "a", "b", "c", "d", "e", "f", "g", "h", "現金股利", "股票股利"],
                "data": list(rows),
            }
        ]
    }


def test_tpex_otc_parses_payload():
    payload = _tpex_payload(
        ["115/06/15", "5483", "x", "y", "z", "a", "b", "c", "d", "e", "f", "g", "h", "8.0", "0"],
    )
    rows = tpex_otc.parse_tpex_otc(payload)
    assert len(rows) == 1
    assert rows[0].symbol == "5483"
    assert rows[0].ex_dividend_date == date(2026, 6, 15)
    assert rows[0].cash_dividend == Decimal("8.0")
    assert rows[0].stock_dividend is None
    assert rows[0].source == "TPEX_OTC"


def test_tpex_otc_stock_per_thousand_to_per_share():
    """cells[14] is shares per 1000 (TPEx convention) — divide by 1000."""
    payload = _tpex_payload(
        ["115/06/15", "5483", "x", "y", "z", "a", "b", "c", "d", "e", "f", "g", "h", "0", "500"],
    )
    rows = tpex_otc.parse_tpex_otc(payload)
    assert rows[0].stock_dividend == Decimal("0.5")
    assert rows[0].cash_dividend is None


def test_tpex_otc_skips_short_rows():
    payload = _tpex_payload(["115/06/15", "5483"])  # only 2 cells
    assert tpex_otc.parse_tpex_otc(payload) == []


def test_tpex_otc_skips_missing_date():
    payload = _tpex_payload(
        ["", "5483", "x", "y", "z", "a", "b", "c", "d", "e", "f", "g", "h", "1", "0"],
    )
    assert tpex_otc.parse_tpex_otc(payload) == []


def test_tpex_otc_accepts_bytes():
    raw = json.dumps(_tpex_payload(
        ["115/06/15", "5483", "x", "y", "z", "a", "b", "c", "d", "e", "f", "g", "h", "8", "0"],
    )).encode("utf-8")
    rows = tpex_otc.parse_tpex_otc(raw)
    assert len(rows) == 1
