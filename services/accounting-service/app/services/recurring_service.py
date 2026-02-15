from sqlalchemy.orm import Session
from sqlalchemy import extract
from datetime import date
from .. import models
import logging

logger = logging.getLogger(__name__)

def generate_recurring_items(db: Session):
    """
    產生本月的訂閱與分期 PENDING 項目。
    具備等冪性 (Idempotency)，重複執行不會產生重複數據。
    """
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    # --- 1. 處理訂閱項目 (Subscription) ---
    subs = db.query(models.Subscription).filter(models.Subscription.active == True).all()
    for sub in subs:
        # 檢查本月是否已存在該訂閱的交易紀錄 (不論狀態)
        exists = db.query(models.Transaction).filter(
            models.Transaction.subscription_id == sub.id,
            extract('year', models.Transaction.date) == current_year,
            extract('month', models.Transaction.date) == current_month,
            models.Transaction.is_deleted == False
        ).first()
        
        if not exists:
            logger.info(f"自動生成本月訂閱項目: {sub.name}")
            day = min(sub.day_of_month, 28)
            new_pending = models.Transaction(
                date=today.replace(day=day),
                category=sub.category,
                item=sub.name,
                personal_amount=sub.amount,
                actual_swipe=sub.amount,
                payment_method="Automatic",
                card_id=sub.card_id,
                status="PENDING_SUB",
                subscription_id=sub.id,
                transaction_type="EXPENSE"
            )
            db.add(new_pending)

    # --- 2. 處理分期項目 (Installment) ---
    insts = db.query(models.Installment).filter(models.Installment.remaining_periods > 0).all()
    for inst in insts:
        # 檢查本月是否已存在
        exists = db.query(models.Transaction).filter(
            models.Transaction.installment_id == inst.id,
            extract('year', models.Transaction.date) == current_year,
            extract('month', models.Transaction.date) == current_month,
            models.Transaction.is_deleted == False
        ).first()
        
        if not exists:
            # 計算目前是第幾期 (總期數 - 剩餘期數 + 1)
            current_period = inst.total_periods - inst.remaining_periods + 1
            item_name = f"{inst.name} (第 {current_period}/{inst.total_periods} 期)"
            
            logger.info(f"自動生成本月分期項目: {item_name}")
            day = min(inst.start_date.day, 28)
            new_pending = models.Transaction(
                date=today.replace(day=day),
                category="分期付款",
                item=item_name,
                personal_amount=inst.monthly_amount,
                actual_swipe=inst.monthly_amount,
                payment_method="Automatic",
                card_id=inst.card_id,
                status="PENDING_INSTALLMENT",
                installment_id=inst.id,
                transaction_type="EXPENSE"
            )
            db.add(new_pending)
            
            # 遞減剩餘期數
            inst.remaining_periods -= 1

    db.commit()
