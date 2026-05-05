from datetime import date
from decimal import Decimal
from unittest.mock import patch

from app.services.portfolio_service import _calculate_xirr


class TestCalculateXirr:
    def test_simple_profitable_investment(self):
        """Sanity check against the real pyxirr library: ~20% annualised."""
        cash_flows = [
            (date(2025, 1, 1), Decimal("-10000")),
            (date(2026, 1, 1), Decimal("12000")),
        ]
        result = _calculate_xirr(cash_flows)
        assert result is not None
        assert Decimal("0.15") < result < Decimal("0.25")

    def test_investment_with_dividend(self):
        cash_flows = [
            (date(2025, 1, 1), Decimal("-10000")),
            (date(2025, 7, 1), Decimal("500")),
            (date(2026, 1, 1), Decimal("11000")),
        ]
        result = _calculate_xirr(cash_flows)
        assert result is not None
        assert result > Decimal("0.15")

    def test_single_cashflow_returns_none(self):
        cash_flows = [
            (date(2025, 1, 1), Decimal("-10000")),
        ]
        assert _calculate_xirr(cash_flows) is None

    def test_all_same_date_returns_none(self):
        cash_flows = [
            (date(2025, 1, 1), Decimal("-10000")),
            (date(2025, 1, 1), Decimal("12000")),
        ]
        assert _calculate_xirr(cash_flows) is None

    def test_zero_terminal_value_returns_none(self):
        cash_flows = [
            (date(2025, 1, 1), Decimal("-10000")),
            (date(2026, 1, 1), Decimal("0")),
        ]
        assert _calculate_xirr(cash_flows) is None


class TestCalculateXirrDecimalContract:
    """Pin the Decimal contract around the float boundary in _calculate_xirr.

    pyxirr is float-only. These tests mock it to a deterministic float and
    assert that the wrapper's Decimal coercion + 6-digit rounding produces an
    exact Decimal value. Any future float drift (e.g. accidental float
    arithmetic on the input or output) will break these.
    """

    @staticmethod
    def _two_flow_args():
        return [
            (date(2025, 1, 1), Decimal("-10000")),
            (date(2026, 1, 1), Decimal("12000")),
        ]

    def test_returns_exact_decimal_rounded_to_six_places(self):
        with patch("pyxirr.xirr", return_value=0.18234567):
            assert _calculate_xirr(self._two_flow_args()) == Decimal("0.182346")

    def test_returns_exact_decimal_for_clean_value(self):
        with patch("pyxirr.xirr", return_value=0.15):
            assert _calculate_xirr(self._two_flow_args()) == Decimal("0.15")

    def test_returns_none_for_nan(self):
        with patch("pyxirr.xirr", return_value=float("nan")):
            assert _calculate_xirr(self._two_flow_args()) is None

    def test_returns_none_for_inf(self):
        with patch("pyxirr.xirr", return_value=float("inf")):
            assert _calculate_xirr(self._two_flow_args()) is None

    def test_returns_none_when_pyxirr_returns_non_float(self):
        with patch("pyxirr.xirr", return_value=None):
            assert _calculate_xirr(self._two_flow_args()) is None

    def test_passes_float_cashflows_to_pyxirr(self):
        captured = {}

        def fake_xirr(dates, amounts):
            captured["dates"] = list(dates)
            captured["amounts"] = list(amounts)
            return 0.1

        with patch("pyxirr.xirr", side_effect=fake_xirr):
            _calculate_xirr(self._two_flow_args())

        assert all(isinstance(amount, float) for amount in captured["amounts"])
        assert captured["amounts"] == [-10000.0, 12000.0]
