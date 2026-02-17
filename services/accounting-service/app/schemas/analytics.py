from . import BaseSchema
from typing import List
from datetime import date as dt_date
from .transaction import Transaction

class CategorySummary(BaseSchema):
    category: str
    amount: int
    percentage: float

class PaymentMethodSummary(BaseSchema):
    method: str
    amount: int

class MonthlyReportSummary(BaseSchema):
    total_income: int
    total_expense: int
    surplus: int
    savings_rate: float

class CardUsageSummary(BaseSchema):
    card_name: str
    billing_cycle_start: dt_date
    billing_cycle_end: dt_date
    current_usage: int
    alert_threshold: int
    usage_percentage: float
    remaining_to_threshold: int
    is_near_limit: bool
    is_over_limit: bool

class MonthlyReport(BaseSchema):
    period: str
    summary: MonthlyReportSummary
    expense_breakdown: List[CategorySummary]
    payment_breakdown: List[PaymentMethodSummary]
    top_expenses: List[Transaction]


class CategoryDeltaSummary(BaseSchema):
    category: str
    current_amount: int
    previous_amount: int
    delta_amount: int
    delta_percent: float
    status: str  # up/down/new/gone/flat


class MonthlyCompareSummary(BaseSchema):
    total_expense_delta: int
    top_increase_category: str | None = None
    top_decrease_category: str | None = None


class MonthlyCompareReport(BaseSchema):
    period: str
    baseline_period: str
    categories: List[CategoryDeltaSummary]
    summary: MonthlyCompareSummary
