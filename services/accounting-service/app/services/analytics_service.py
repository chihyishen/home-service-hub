from sqlalchemy.orm import Session
from sqlalchemy import func, extract, or_
from datetime import date, timedelta
from .. import models, schemas
from . import recurring_service, billing_service
from typing import List

def get_card_usage_summary(db: Session) -> List[schemas.analytics.CardUsageSummary]:
    today = date.today()
    
    # 取得所有信用卡
    cards = db.query(models.CreditCard).all()
    
    summaries = []
    
    for card in cards:
        # 計算回饋週期
        start_date, end_date = billing_service.get_reward_cycle_range(card, today)

        # 查詢週期內的消費總額
        # 條件: (card_id = card.id) OR (payment_method = card.name)
        # 且為 EXPENSE, 未取消
        usage_query = db.query(func.sum(models.Transaction.personal_amount)).filter(
            models.Transaction.date >= start_date,
            models.Transaction.date <= end_date,
            models.Transaction.transaction_type == "EXPENSE",
            models.Transaction.status != "CANCELLED",
            or_(
                models.Transaction.card_id == card.id,
                models.Transaction.payment_method == card.name
            )
        )
        
        current_usage = usage_query.scalar() or 0.0
        
        threshold = card.alert_threshold or 20000.0 # 預設 2萬
        percentage = (current_usage / threshold * 100) if threshold > 0 else 0.0
        
        summaries.append(schemas.analytics.CardUsageSummary(
            card_name=card.name,
            billing_cycle_start=start_date,
            billing_cycle_end=end_date,
            current_usage=current_usage,
            alert_threshold=threshold,
            usage_percentage=percentage
        ))
        
    return summaries

def get_monthly_report(db: Session, year: int, month: int) -> schemas.MonthlyReport:
    # 【自動補償】在產生報表前，確保本月的定期項目都已經生成 PENDING
    # 這樣報表才會包含預計支出
    today = date.today()
    if year == today.year and month == today.month:
        recurring_service.generate_recurring_items(db)

    # 1. 取得當月所有未刪除交易
    transactions = db.query(models.Transaction).filter(
        extract('year', models.Transaction.date) == year,
        extract('month', models.Transaction.date) == month
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
