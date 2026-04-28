from sqlalchemy.orm import Session
from sqlalchemy import extract
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

        current_usage = billing_service.get_card_cycle_usage(db, card, start_date, end_date)
        
        threshold = card.alert_threshold or 20000.0 # 預設 2萬
        percentage = (current_usage / threshold * 100) if threshold > 0 else 0.0
        remaining = max(0, int(threshold - current_usage))
        is_near_limit = percentage >= 80 and percentage < 100
        is_over_limit = percentage >= 100
        
        summaries.append(schemas.analytics.CardUsageSummary(
            card_name=card.name,
            billing_cycle_start=start_date,
            billing_cycle_end=end_date,
            current_usage=int(current_usage),
            alert_threshold=int(threshold),
            usage_percentage=percentage,
            remaining_to_threshold=remaining,
            is_near_limit=is_near_limit,
            is_over_limit=is_over_limit
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
            total_income += t.paid_amount
        else:
            total_expense += t.paid_amount
            # 統計分類
            category_map[t.category] = category_map.get(t.category, 0.0) + t.paid_amount
            
            # 統計支付來源 (以卡片名稱為準，若無卡片則使用支付方式名稱如「現金」)
            p_source = t.card.name if t.card_id and t.card else t.payment_method
            payment_map[p_source] = payment_map.get(p_source, 0.0) + t.paid_amount

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
        key=lambda x: x.transaction_amount,
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


def get_monthly_compare_report(db: Session, year: int, month: int) -> schemas.analytics.MonthlyCompareReport:
    current_month_txns = db.query(models.Transaction).filter(
        extract('year', models.Transaction.date) == year,
        extract('month', models.Transaction.date) == month,
        models.Transaction.transaction_type == "EXPENSE"
    ).all()

    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    previous_month_txns = db.query(models.Transaction).filter(
        extract('year', models.Transaction.date) == prev_year,
        extract('month', models.Transaction.date) == prev_month,
        models.Transaction.transaction_type == "EXPENSE"
    ).all()

    current_map: dict[str, int] = {}
    previous_map: dict[str, int] = {}

    for t in current_month_txns:
        current_map[t.category] = current_map.get(t.category, 0) + int(t.transaction_amount or 0)

    for t in previous_month_txns:
        previous_map[t.category] = previous_map.get(t.category, 0) + int(t.transaction_amount or 0)

    all_categories = sorted(set(current_map.keys()) | set(previous_map.keys()))
    category_deltas: list[schemas.analytics.CategoryDeltaSummary] = []

    for category in all_categories:
        current_amount = current_map.get(category, 0)
        previous_amount = previous_map.get(category, 0)
        delta_amount = current_amount - previous_amount

        if previous_amount == 0 and current_amount > 0:
            status = "new"
            delta_percent = 100.0
        elif previous_amount > 0 and current_amount == 0:
            status = "gone"
            delta_percent = -100.0
        elif delta_amount > 0:
            status = "up"
            delta_percent = (delta_amount / previous_amount * 100) if previous_amount > 0 else 0.0
        elif delta_amount < 0:
            status = "down"
            delta_percent = (delta_amount / previous_amount * 100) if previous_amount > 0 else 0.0
        else:
            status = "flat"
            delta_percent = 0.0

        category_deltas.append(
            schemas.analytics.CategoryDeltaSummary(
                category=category,
                current_amount=current_amount,
                previous_amount=previous_amount,
                delta_amount=delta_amount,
                delta_percent=delta_percent,
                status=status
            )
        )

    category_deltas.sort(key=lambda x: abs(x.delta_amount), reverse=True)

    top_increase = next((c for c in category_deltas if c.delta_amount > 0), None)
    top_decrease = next((c for c in category_deltas if c.delta_amount < 0), None)
    total_expense_delta = sum(current_map.values()) - sum(previous_map.values())

    return schemas.analytics.MonthlyCompareReport(
        period=f"{year}-{month:02d}",
        baseline_period=f"{prev_year}-{prev_month:02d}",
        categories=category_deltas,
        summary=schemas.analytics.MonthlyCompareSummary(
            total_expense_delta=total_expense_delta,
            top_increase_category=top_increase.category if top_increase else None,
            top_decrease_category=top_decrease.category if top_decrease else None
        )
    )
