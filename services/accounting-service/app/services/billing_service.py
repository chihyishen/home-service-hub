from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from .. import models, schemas

def safe_date_replace(year, month, day):
    """
    安全地處理日期替換，若該月無此日則取該月最後一天
    """
    import calendar
    _, last_day = calendar.monthrange(year, month)
    return date(year, month, min(day, last_day))

def get_billing_cycle_range(billing_day: int, target_date: date):
    """
    根據結帳日計算目標日期所屬的帳單週期範圍
    """
    if target_date.day > billing_day:
        # 在本月結帳日之後：週期是 [本月結帳+1, 下月結帳]
        start_date = safe_date_replace(target_date.year, target_date.month, billing_day + 1)
        if target_date.month == 12:
            end_date = safe_date_replace(target_date.year + 1, 1, billing_day)
        else:
            end_date = safe_date_replace(target_date.year, target_date.month + 1, billing_day)
    else:
        # 在本月結帳日之前(或當天)：週期是 [上月結帳+1, 本月結帳]
        if target_date.month == 1:
            start_date = safe_date_replace(target_date.year - 1, 12, billing_day + 1)
        else:
            start_date = safe_date_replace(target_date.year, target_date.month - 1, billing_day + 1)
        end_date = safe_date_replace(target_date.year, target_date.month, billing_day)
    
    return start_date, end_date

def get_reward_cycle_range(card: models.CreditCard, target_date: date):
    """
    根據卡片的回饋週期類型計算日期範圍
    """
    if card.reward_cycle_type == "CALENDAR_MONTH":
        import calendar
        start_date = date(target_date.year, target_date.month, 1)
        _, last_day = calendar.monthrange(target_date.year, target_date.month)
        end_date = date(target_date.year, target_date.month, last_day)
        return start_date, end_date
    
    return get_billing_cycle_range(card.billing_day, target_date)

def get_card_status(db: Session, card_id: int):
    card = db.query(models.CreditCard).filter(
        models.CreditCard.id == card_id
    ).first()
    if not card:
        return None
    
    today = date.today()
    start_date, end_date = get_reward_cycle_range(card, today)
    
    current_usage = db.query(func.sum(models.Transaction.transaction_amount)).filter(
        models.Transaction.card_id == card_id,
        models.Transaction.date >= start_date,
        models.Transaction.date <= end_date
    ).scalar() or 0.0
    
    remaining = None
    status_msg = f"本期累計已刷 ${current_usage:,.0f}"
    
    if card.reward_rules:
        # 簡單取第一條規則作為範例
        try:
            primary_threshold = card.reward_rules[0].get("threshold", 0)
            if primary_threshold > 0:
                remaining = max(0, primary_threshold - current_usage)
                if remaining > 0:
                    status_msg += f"，距離最高優惠上限還差 ${remaining:,.0f}"
                else:
                    status_msg += "，已達最高優惠上限 ⚠️"
        except (IndexError, AttributeError):
            pass

    # 確保回傳時日期轉為字串以匹配 Schema (如果必要)
    return schemas.CardStatus(
        card_name=card.name,
        current_cycle_total=current_usage,
        remaining_for_max_reward=remaining,
        next_billing_date=end_date.strftime("%Y-%m-%d"),
        status_message=status_msg
    )
