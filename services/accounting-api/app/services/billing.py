from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, schemas

def get_billing_cycle_range(billing_day: int, target_date: date):
    """
    根據結帳日計算目標日期所屬的帳單週期範圍
    """
    if target_date.day > billing_day:
        start_date = target_date.replace(day=billing_day + 1)
        # 處理跨月
        if target_date.month == 12:
            end_date = target_date.replace(year=target_date.year + 1, month=1, day=billing_day)
        else:
            end_date = target_date.replace(month=target_date.month + 1, day=billing_day)
    else:
        # 在結帳日之前
        if target_date.month == 1:
            start_date = target_date.replace(year=target_date.year - 1, month=12, day=billing_day + 1)
        else:
            start_date = target_date.replace(month=target_date.month - 1, day=billing_day + 1)
        end_date = target_date.replace(day=billing_day)
    
    return start_date, end_date

def get_card_status(db: Session, card_id: int):
    card = db.query(models.CreditCard).filter(models.CreditCard.id == card_id).first()
    if not card:
        return None
    
    today = date.today()
    start_date, end_date = get_billing_cycle_range(card.billing_day, today)
    
    # 計算本期已刷總額 (含 Pending 項目)
    current_usage = db.query(func.sum(models.Transaction.actual_swipe)).filter(
        models.Transaction.card_id == card_id,
        models.Transaction.date >= start_date,
        models.Transaction.date <= end_date
    ).scalar() or 0.0
    
    # 計算剩餘優惠額度
    remaining = None
    status_msg = f"本期累計已刷 ${current_usage:,.0f}"
    
    if card.reward_rules:
        # 假設第一條規則通常是最高優惠上限
        primary_threshold = card.reward_rules[0].get("threshold", 0)
        if primary_threshold > 0:
            remaining = max(0, primary_threshold - current_usage)
            if remaining > 0:
                status_msg += f"，距離最高優惠上限還差 ${remaining:,.0f}"
            else:
                status_msg += "，已達最高優惠上限 ⚠️"

    return schemas.CardStatus(
        card_name=card.name,
        current_cycle_total=current_usage,
        remaining_for_max_reward=remaining,
        next_billing_date=end_date,
        status_message=status_msg
    )
