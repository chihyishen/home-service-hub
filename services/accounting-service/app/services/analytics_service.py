from datetime import date

from sqlalchemy import extract
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from . import billing_service
from .refund_utils import get_refunded_amounts


def _category_name(transaction: models.Transaction) -> str:
    return transaction.category_info.name


def _populate_top_expense_fields(db: Session, transactions: list[models.Transaction]) -> None:
    refunded_amounts = get_refunded_amounts(db, [transaction.id for transaction in transactions])

    for transaction in transactions:
        transaction.card_name = transaction.card.name if transaction.card else None
        if transaction.transaction_type == "EXPENSE":
            transaction.refundable_amount = max(int(transaction.transaction_amount or 0) - refunded_amounts.get(transaction.id, 0), 0)
        else:
            transaction.refundable_amount = 0


def _get_net_expense_amount(transaction: models.Transaction, refunded_amounts: dict[int, int]) -> int:
    original_amount = int(transaction.paid_amount or 0)
    return max(original_amount - refunded_amounts.get(transaction.id, 0), 0)


def _is_refund_income(transaction: models.Transaction) -> bool:
    return transaction.transaction_type == "INCOME" and transaction.related_transaction_id is not None


def _ensure_category_month_bucket(category_monthly_map: dict[str, list[int]], category_name: str) -> None:
    if category_name not in category_monthly_map:
        category_monthly_map[category_name] = [0] * 12


def _get_visible_annual_month_indices(year: int) -> list[int]:
    today = date.today()
    if year > today.year:
        return []
    if year == today.year:
        return list(range(today.month))
    return list(range(12))

def get_card_usage_summary(db: Session) -> list[schemas.analytics.CardUsageSummary]:
    today = date.today()
    
    # 取得所有信用卡
    cards = db.query(models.CreditCard).all()
    
    summaries = []
    
    for card in cards:
        # 計算回饋週期
        start_date, end_date = billing_service.get_reward_cycle_range(card, today)

        current_usage = billing_service.get_card_cycle_usage(db, card, start_date, end_date)
        
        threshold = int(card.alert_threshold or 20000) # 預設 2萬
        positive_usage = max(current_usage, 0)
        percentage = (positive_usage / threshold * 100) if threshold > 0 else 0.0
        remaining = max(0, threshold - positive_usage)
        is_near_limit = current_usage > 0 and percentage >= 80 and percentage < 100
        is_over_limit = current_usage > 0 and percentage >= 100
        
        summaries.append(schemas.analytics.CardUsageSummary(
            card_name=card.name,
            billing_cycle_start=start_date,
            billing_cycle_end=end_date,
            current_usage=int(current_usage),
            alert_threshold=threshold,
            usage_percentage=percentage,
            remaining_to_threshold=remaining,
            is_near_limit=is_near_limit,
            is_over_limit=is_over_limit
        ))
        
    return summaries


def get_annual_report(db: Session, year: int) -> schemas.analytics.AnnualReport:
    visible_month_indices = _get_visible_annual_month_indices(year)
    transactions = (
        db.query(models.Transaction)
        .options(
            joinedload(models.Transaction.card),
            joinedload(models.Transaction.category_info),
        )
        .filter(extract('year', models.Transaction.date) == year)
        .all()
    )

    monthly_income = [0] * 12
    monthly_expense = [0] * 12
    category_monthly_map: dict[str, list[int]] = {}
    visible_month_count = len(visible_month_indices)
    expense_transactions = [t for t in transactions if t.transaction_type == "EXPENSE"]
    refunded_amounts = get_refunded_amounts(db, [transaction.id for transaction in expense_transactions])

    for transaction in transactions:
        month_index = transaction.date.month - 1
        amount = int(transaction.paid_amount or 0)

        if transaction.transaction_type == "INCOME":
            if _is_refund_income(transaction):
                continue
            monthly_income[month_index] += amount
            continue

        category_name = _category_name(transaction)
        _ensure_category_month_bucket(category_monthly_map, category_name)

        net_amount = _get_net_expense_amount(transaction, refunded_amounts)
        monthly_expense[month_index] += net_amount
        category_monthly_map[category_name][month_index] += net_amount

    monthly_trend = [
        schemas.analytics.MonthlyTrendPoint(
            month=f"{year}-{month_index + 1:02d}",
            total_income=monthly_income[month_index],
            total_expense=monthly_expense[month_index],
            surplus=monthly_income[month_index] - monthly_expense[month_index],
        )
        for month_index in visible_month_indices
    ]

    category_trend = [
        schemas.analytics.CategoryTrend(
            category=category_name,
            monthly_amounts=[monthly_amounts[month_index] for month_index in visible_month_indices],
            total=sum(monthly_amounts[month_index] for month_index in visible_month_indices),
            average=(sum(monthly_amounts[month_index] for month_index in visible_month_indices) // visible_month_count) if visible_month_count > 0 else 0,
        )
        for category_name, monthly_amounts in category_monthly_map.items()
    ]
    category_trend.sort(key=lambda item: item.total, reverse=True)

    total_income = sum(monthly_income[month_index] for month_index in visible_month_indices)
    total_expense = sum(monthly_expense[month_index] for month_index in visible_month_indices)
    surplus = total_income - total_expense
    positive_expense_months = [month_index for month_index in visible_month_indices if monthly_expense[month_index] > 0]

    highest_expense_month = None
    lowest_expense_month = None
    if positive_expense_months:
        highest_index = max(positive_expense_months, key=lambda index: monthly_expense[index])
        lowest_index = min(positive_expense_months, key=lambda index: monthly_expense[index])
        highest_expense_month = f"{year}-{highest_index + 1:02d}"
        lowest_expense_month = f"{year}-{lowest_index + 1:02d}"

    return schemas.analytics.AnnualReport(
        year=year,
        monthly_trend=monthly_trend,
        category_trend=category_trend,
        summary=schemas.analytics.AnnualSummary(
            total_income=total_income,
            total_expense=total_expense,
            surplus=surplus,
            savings_rate=(surplus / total_income * 100) if total_income > 0 else 0.0,
            highest_expense_month=highest_expense_month,
            lowest_expense_month=lowest_expense_month,
        ),
    )

def get_monthly_report(db: Session, year: int, month: int) -> schemas.MonthlyReport:
    # 1. 取得當月所有未刪除交易
    transactions = (
        db.query(models.Transaction)
        .options(
            joinedload(models.Transaction.card),
            joinedload(models.Transaction.category_info),
        )
        .filter(
            extract('year', models.Transaction.date) == year,
            extract('month', models.Transaction.date) == month
        )
        .all()
    )

    total_income = 0
    total_expense = 0
    category_map: dict[str, int] = {}
    payment_map: dict[str, int] = {}
    expense_transactions = [t for t in transactions if t.transaction_type == "EXPENSE"]
    refunded_amounts = get_refunded_amounts(db, [transaction.id for transaction in expense_transactions])

    for t in transactions:
        amount = int(t.paid_amount or 0)
        if t.transaction_type == "INCOME":
            if not _is_refund_income(t):
                total_income += amount
            continue

        net_amount = _get_net_expense_amount(t, refunded_amounts)
        total_expense += net_amount
        if net_amount <= 0:
            continue

        # 統計分類
        category_name = _category_name(t)
        category_map[category_name] = category_map.get(category_name, 0) + net_amount

        # 統計支付來源 (以卡片名稱為準，若無卡片則使用支付方式名稱如「現金」)
        p_source = t.card.name if t.card else (t.payment_method or "未知")
        payment_map[p_source] = payment_map.get(p_source, 0) + net_amount

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
    _populate_top_expense_fields(db, top_expenses)

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
    current_month_txns = (
        db.query(models.Transaction)
        .options(joinedload(models.Transaction.category_info))
        .filter(
            extract('year', models.Transaction.date) == year,
            extract('month', models.Transaction.date) == month,
            models.Transaction.transaction_type == "EXPENSE"
        )
        .all()
    )

    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    previous_month_txns = (
        db.query(models.Transaction)
        .options(joinedload(models.Transaction.category_info))
        .filter(
            extract('year', models.Transaction.date) == prev_year,
            extract('month', models.Transaction.date) == prev_month,
            models.Transaction.transaction_type == "EXPENSE"
        )
        .all()
    )

    current_map: dict[str, int] = {}
    previous_map: dict[str, int] = {}
    refunded_amounts = get_refunded_amounts(
        db,
        [transaction.id for transaction in current_month_txns + previous_month_txns],
    )

    for t in current_month_txns:
        net_amount = _get_net_expense_amount(t, refunded_amounts)
        if net_amount <= 0:
            continue
        category_name = _category_name(t)
        current_map[category_name] = current_map.get(category_name, 0) + net_amount

    for t in previous_month_txns:
        net_amount = _get_net_expense_amount(t, refunded_amounts)
        if net_amount <= 0:
            continue
        category_name = _category_name(t)
        previous_map[category_name] = previous_map.get(category_name, 0) + net_amount

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
