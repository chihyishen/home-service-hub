from sqlalchemy.orm import Session
from datetime import date
from .. import models

def generate_recurring_items(db: Session):
    """
    產生本月的訂閱與分期 PENDING 項目
    """
    today = date.today()
    
    # 1. 訂閱項目
    subs = db.query(models.Subscription).filter(models.Subscription.active == True).all()
    for sub in subs:
        # 檢查本月是否已存在 (且未刪除)
        exists = db.query(models.Transaction).filter(
            models.Transaction.subscription_id == sub.id,
            models.Transaction.date >= today.replace(day=1),
            models.Transaction.is_deleted == False
        ).first()
        
        if not exists:
            new_pending = models.Transaction(
                date=today.replace(day=sub.day_of_month),
                category=sub.category,
                item=sub.name,
                personal_amount=sub.amount,
                actual_swipe=sub.amount,
                payment_method="Automatic",
                card_id=sub.card_id,
                status="PENDING_SUB",
                subscription_id=sub.id
            )
            db.add(new_pending)

    # 2. 分期項目 (簡化實作)
    insts = db.query(models.Installment).filter(models.Installment.remaining_periods > 0).all()
    for inst in insts:
        # 檢查本月是否已存在
        exists = db.query(models.Transaction).filter(
            models.Transaction.installment_id == inst.id,
            models.Transaction.date >= today.replace(day=1),
            models.Transaction.is_deleted == False
        ).first()
        
        if not exists:
            # 這裡可以加入遞減 remaining_periods 的邏輯，但為了 Phase 3 暫不變動
            pass
        
    db.commit()
