from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import date
from .. import models, schemas
from typing import List

def get_monthly_report(db: Session, year: int, month: int) -> schemas.MonthlyReport:
    # 1. 取得當月所有未刪除交易
    transactions = db.query(models.Transaction).filter(
        extract('year', models.Transaction.date) == year,
        extract('month', models.Transaction.date) == month,
        models.Transaction.is_deleted == False
    ).all()

    total_income = 0.0
    total_expense = 0.0
    category_map = {}
    payment_map = {}

    for t in transactions:
        if t.transaction_type == "INCOME":
            total_income += t.personal_amount
        else:
            total_expense += t.personal_amount
            # 統計分類
            category_map[t.category] = category_map.get(t.category, 0.0) + t.personal_amount
            # 統計支付方式
            p_method = t.payment_method
            payment_map[p_method] = payment_map.get(p_method, 0.0) + t.personal_amount

    surplus = total_income - total_expense
    savings_rate = (surplus / total_income * 100) if total_income > 0 else 0.0

    # 格式化分類統計
    expense_breakdown = [
        schemas.analytics.CategorySummary(
            category=cat,
            amount=amt,
            percentage=(amt / total_expense * 100) if total_expense > 0 else 0.0
        ) for cat, amt in sorted(category_map.items(), key=lambda x: x[1], reverse=True)
    ]

    # 格式化支付方式統計
    payment_breakdown = [
        schemas.analytics.PaymentMethodSummary(
            method=met,
            amount=amt
        ) for met, amt in sorted(payment_map.items(), key=lambda x: x[1], reverse=True)
    ]

    # 取得前五大支出
    top_expenses = sorted(
        [t for t in transactions if t.transaction_type == "EXPENSE"],
        key=lambda x: x.personal_amount,
        reverse=True
    )[:5]

    return schemas.MonthlyReport(
        period=f"{year}-{month:02d}",
        summary=schemas.analytics.MonthlyReportSummary(
            total_income=total_income,
            total_expense=total_expense,
            surplus=surplus,
            savings_rate=savings_rate
        ),
        expense_breakdown=expense_breakdown,
        payment_breakdown=payment_breakdown,
        top_expenses=top_expenses
    )
