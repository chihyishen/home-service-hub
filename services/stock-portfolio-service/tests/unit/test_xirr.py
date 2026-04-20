from datetime import date
from decimal import Decimal
from app.services.portfolio_service import _calculate_xirr


class TestCalculateXirr:
    def test_simple_profitable_investment(self):
        """Buy 100 shares at 100, receive 12000 market value 1 year later → ~20% XIRR"""
        cash_flows = [
            (date(2025, 1, 1), Decimal("-10000")),
            (date(2026, 1, 1), Decimal("12000")),
        ]
        result = _calculate_xirr(cash_flows)
        assert result is not None
        assert Decimal("0.15") < result < Decimal("0.25")

    def test_investment_with_dividend(self):
        """Buy at 100, receive 500 dividend, terminal 11000 → XIRR > 15%"""
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
