from app.services.exdividend_service import parse_twse_exdividend_records, roc_to_date
from datetime import date


class TestRocToDate:
    def test_converts_roc_date_string(self):
        assert roc_to_date("114/06/15") == date(2025, 6, 15)

    def test_returns_none_for_empty(self):
        assert roc_to_date("") is None
        assert roc_to_date("-") is None

    def test_returns_none_for_invalid(self):
        assert roc_to_date("not-a-date") is None


class TestParseTwseExdividendRecords:
    def test_parses_valid_records(self):
        raw = [
            {"股票代號": "2330", "名稱": "台積電", "除息交易日": "114/07/17", "除權交易日": "", "最近一次配息": "3.00"},
            {"股票代號": "0050", "名稱": "元大台灣50", "除息交易日": "114/07/20", "除權交易日": "", "最近一次配息": "2.50"},
        ]
        results = parse_twse_exdividend_records(raw, {"2330", "0050"})
        assert len(results) == 2
        assert results[0].symbol == "2330"
        assert results[0].ex_dividend_date == date(2025, 7, 17)
        assert results[0].cash_dividend == "3.00"

    def test_filters_to_held_symbols_only(self):
        raw = [
            {"股票代號": "2330", "名稱": "台積電", "除息交易日": "114/07/17", "除權交易日": "", "最近一次配息": "3.00"},
            {"股票代號": "9999", "名稱": "不持有", "除息交易日": "114/07/20", "除權交易日": "", "最近一次配息": "1.00"},
        ]
        results = parse_twse_exdividend_records(raw, {"2330"})
        assert len(results) == 1
        assert results[0].symbol == "2330"

    def test_returns_empty_for_no_match(self):
        raw = [
            {"股票代號": "9999", "名稱": "不持有", "除息交易日": "114/07/20", "除權交易日": "", "最近一次配息": "1.00"},
        ]
        results = parse_twse_exdividend_records(raw, {"2330"})
        assert results == []

    def test_skips_records_with_no_date(self):
        raw = [
            {"股票代號": "2330", "名稱": "台積電", "除息交易日": "", "除權交易日": "", "最近一次配息": "3.00"},
        ]
        results = parse_twse_exdividend_records(raw, {"2330"})
        assert results == []
