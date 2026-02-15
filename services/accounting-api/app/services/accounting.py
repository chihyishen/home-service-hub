from sqlalchemy.orm import Session
from datetime import date
from .. import models, schemas

def create_transaction(db: Session, transaction: schemas.TransactionCreate):
    # 1. 檢查是否有匹配的 PENDING 項目 (訂閱或分期)
    pending_item = db.query(models.Transaction).filter(
        models.Transaction.status.like("PENDING_%"),
        models.Transaction.item == transaction.item,
        models.Transaction.actual_swipe == transaction.actual_swipe,
        models.Transaction.date >= date.today().replace(day=1) # 當月
    ).first()

    if pending_item:
        # 更新現有 PENDING 項目為 COMPLETED
        for var, value in vars(transaction).items():
            setattr(pending_item, var, value) if value else None
        pending_item.status = "COMPLETED"
        db.commit()
        db.refresh(pending_item)
        return pending_item

    # 2. 如果沒有匹配，檢查支付通路路由
    db_transaction = models.Transaction(**transaction.dict())
    
    # 自動補全 card_id 如果 payment_method 有映射
    if not db_transaction.card_id:
        route = db.query(models.PaymentRoute).filter(
            models.PaymentRoute.method_name == transaction.payment_method
        ).first()
        if route:
            db_transaction.card_id = route.card_id

    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def generate_recurring_items(db: Session):
    """
    產生本月的訂閱與分期 PENDING 項目
    """
    today = date.today()
    
    # 訂閱項目
    subs = db.query(models.Subscription).filter(models.Subscription.active == True).all()
    for sub in subs:
        # 檢查本月是否已存在
        exists = db.query(models.Transaction).filter(
            models.Transaction.subscription_id == sub.id,
            models.Transaction.date >= today.replace(day=1)
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

    # 分期項目
    insts = db.query(models.Installment).filter(models.Installment.remaining_periods > 0).all()
    for inst in insts:
        # 邏輯類似... 略過詳細檢查，直接示範建立
        pass
        
    db.commit()
