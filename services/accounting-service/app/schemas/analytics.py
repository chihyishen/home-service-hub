from pydantic import BaseModel, Field
from typing import List
from .transaction import Transaction

class CategorySummary(BaseModel):
    category: str
    amount: float
    percentage: float

class PaymentMethodSummary(BaseModel):
    method: str
    amount: float

class MonthlyReportSummary(BaseModel):
    total_income: float
    total_expense: float
    surplus: float
    savings_rate: float

class MonthlyReport(BaseModel):
    period: str
    summary: MonthlyReportSummary
    expense_breakdown: List[CategorySummary]
    payment_breakdown: List[PaymentMethodSummary]
    top_expenses: List[Transaction]
