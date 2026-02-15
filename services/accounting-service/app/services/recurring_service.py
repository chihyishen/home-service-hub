from sqlalchemy.orm import Session
from sqlalchemy import extract
from datetime import date
from .. import models, schemas
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

# --- 自動化生成邏輯 ---

def generate_recurring_items(db: Session):
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    subs = db.query(models.Subscription).filter(
        models.Subscription.active == True,
        models.Subscription.is_deleted == False
    ).all()
    
    for sub in subs:
        exists = db.query(models.Transaction).filter(
            models.Transaction.subscription_id == sub.id,
            extract('year', models.Transaction.date) == current_year,
            extract('month', models.Transaction.date) == current_month,
            models.Transaction.is_deleted == False
        ).first()
        
        if not exists:
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

    insts = db.query(models.Installment).filter(
        models.Installment.remaining_periods > 0,
        models.Installment.is_deleted == False
    ).all()
    
    for inst in insts:
        exists = db.query(models.Transaction).filter(
            models.Transaction.installment_id == inst.id,
            extract('year', models.Transaction.date) == current_year,
            extract('month', models.Transaction.date) == current_month,
            models.Transaction.is_deleted == False
        ).first()
        
        if not exists:
            current_period = inst.total_periods - inst.remaining_periods + 1
            item_name = f"{inst.name} (第 {current_period}/{inst.total_periods} 期)"
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
            inst.remaining_periods -= 1

    db.commit()

# --- 訂閱管理 (Subscription CRUD) ---

def get_subscriptions(db: Session):
    return db.query(models.Subscription).filter(models.Subscription.is_deleted == False).all()

def create_subscription(db: Session, sub: schemas.SubscriptionCreate):
    db_sub = models.Subscription(**sub.model_dump())
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub

def update_subscription(db: Session, sub_id: int, sub_update: schemas.SubscriptionUpdate):
    db_sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    update_data = sub_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_sub, key, value)
    db.commit()
    db.refresh(db_sub)
    return db_sub

def toggle_subscription_active(db: Session, sub_id: int):
    db_sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db_sub.active = not db_sub.active
    db.commit()
    db.refresh(db_sub)
    return db_sub

def delete_subscription(db: Session, sub_id: int):
    db_sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db_sub.is_deleted = True
    db.commit()
    return {"message": "Subscription soft deleted"}

# --- 分期管理 (Installment CRUD) ---

def get_installments(db: Session):
    return db.query(models.Installment).filter(models.Installment.is_deleted == False).all()

def create_installment(db: Session, inst: schemas.InstallmentCreate):
    db_inst = models.Installment(**inst.model_dump())
    db.add(db_inst)
    db.commit()
    db.refresh(db_inst)
    return db_inst

def delete_installment(db: Session, inst_id: int):
    db_inst = db.query(models.Installment).filter(models.Installment.id == inst_id).first()
    if not db_inst:
        raise HTTPException(status_code=404, detail="Installment not found")
    db_inst.is_deleted = True
    db.commit()
    return {"message": "Installment soft deleted"}
