import calendar
from datetime import date, timedelta

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from .. import models, schemas


def safe_date_replace(year, month, day):
    """
    安全地處理日期替換，若該月無此日則取該月最後一天
    """
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, min(day, last_day))


def _effective_closing_date(billing_day: int, year: int, month: int) -> date:
    return safe_date_replace(year, month, billing_day)


def _previous_month(year: int, month: int) -> tuple[int, int]:
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def get_billing_cycle_range(billing_day: int, target_date: date):
    """
    根據結帳日計算目標日期所屬的帳單週期範圍
    """
    current_close = _effective_closing_date(billing_day, target_date.year, target_date.month)
    if target_date <= current_close:
        end_date = current_close
        previous_year, previous_month = _previous_month(target_date.year, target_date.month)
        previous_close = _effective_closing_date(billing_day, previous_year, previous_month)
        start_date = previous_close + timedelta(days=1)
    else:
        next_year, next_month = _next_month(target_date.year, target_date.month)
        end_date = _effective_closing_date(billing_day, next_year, next_month)
        start_date = current_close + timedelta(days=1)

    return start_date, end_date


def get_calendar_month_range(target_date: date):
    start_date = date(target_date.year, target_date.month, 1)
    _, last_day = calendar.monthrange(target_date.year, target_date.month)
    return start_date, date(target_date.year, target_date.month, last_day)


def get_reward_cycle_range(card: models.CreditCard, target_date: date):
    """
    根據卡片的回饋週期類型計算日期範圍
    """
    if card.reward_cycle_type == "CALENDAR_MONTH":
        return get_calendar_month_range(target_date)
    
    return get_billing_cycle_range(card.billing_day, target_date)


def get_alert_cycle_range(card: models.CreditCard, target_date: date):
    """Return the configured alert range, falling back to the reward range."""
    if card.alert_cycle_type == "CALENDAR_MONTH":
        return get_calendar_month_range(target_date)
    if card.alert_cycle_type == "BILLING_CYCLE":
        return get_billing_cycle_range(card.billing_day, target_date)
    return get_reward_cycle_range(card, target_date)


def get_card_cycle_usage(
    db: Session,
    card: models.CreditCard,
    start_date: date,
    end_date: date,
    include_payment_method_alias: bool = True,
    payment_method: str | None = None,
) -> int:
    card_filter = models.Transaction.card_id == card.id
    if payment_method is not None:
        # 指定支付工具時為排他性過濾，不再與卡片別名 OR 在一起
        card_filter = (models.Transaction.card_id == card.id) & (
            models.Transaction.payment_method == payment_method
        )
    elif include_payment_method_alias:
        card_filter = or_(
            card_filter,
            models.Transaction.payment_method == card.name,
        )

    signed_amount = case(
        (models.Transaction.transaction_type == "EXPENSE", models.Transaction.transaction_amount),
        (models.Transaction.transaction_type == "INCOME", -models.Transaction.transaction_amount),
        else_=0,
    )

    current_usage = db.query(func.coalesce(func.sum(signed_amount), 0)).filter(
        models.Transaction.date >= start_date,
        models.Transaction.date <= end_date,
        card_filter,
    ).scalar() or 0

    return int(current_usage)


def get_card_alert_usage(
    db: Session,
    card: models.CreditCard,
    target_date: date,
) -> tuple[int, date, date]:
    start_date, end_date = get_alert_cycle_range(card, target_date)
    usage = get_card_cycle_usage(
        db,
        card,
        start_date,
        end_date,
        payment_method=card.alert_payment_method,
    )
    return usage, start_date, end_date


def get_card_status(db: Session, card_id: int, target_date: date | None = None):
    card = db.query(models.CreditCard).filter(
        models.CreditCard.id == card_id
    ).first()
    if not card:
        return None
    
    today = target_date or date.today()
    start_date, end_date = get_reward_cycle_range(card, today)

    current_usage = get_card_cycle_usage(db, card, start_date, end_date)
    alert_usage, alert_start_date, alert_end_date = get_card_alert_usage(db, card, today)
    filtered_usage = alert_usage if card.alert_payment_method else None

    remaining = None
    if current_usage < 0:
        status_msg = f"本期淨退款 ${abs(current_usage):,.0f}"
    else:
        status_msg = f"本期淨刷卡 ${current_usage:,.0f}"

    if card.alert_threshold > 0:
        effective_usage = max(alert_usage, 0)
        remaining = max(0, card.alert_threshold - effective_usage)
        if card.alert_payment_method:
            if remaining > 0:
                status_msg += f"，{card.alert_payment_method} 已刷 ${effective_usage:,.0f}，距離預警門檻還差 ${remaining:,.0f}"
            else:
                status_msg += f"，{card.alert_payment_method} 已達預警門檻 ⚠️"
        else:
            if remaining > 0:
                status_msg += f"，距離預警門檻還差 ${remaining:,.0f}"
            else:
                status_msg += "，已達預警門檻 ⚠️"

    # 確保回傳時日期轉為字串以匹配 Schema (如果必要)
    return schemas.CardStatus(
        card_name=card.name,
        current_cycle_total=current_usage,
        remaining_for_max_reward=remaining,
        next_billing_date=end_date.strftime("%Y-%m-%d"),
        status_message=status_msg,
        filtered_usage=filtered_usage,
        alert_payment_method=card.alert_payment_method,
        alert_cycle_type=card.alert_cycle_type,
        alert_period_start=alert_start_date.strftime("%Y-%m-%d"),
        alert_period_end=alert_end_date.strftime("%Y-%m-%d"),
    )
