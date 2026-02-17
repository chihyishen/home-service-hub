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
        models.Subscription.active == True
    ).all()
    
    for sub in subs:
        exists = db.query(models.Transaction).filter(
            models.Transaction.subscription_id == sub.id,
            extract('year', models.Transaction.date) == current_year,
            extract('month', models.Transaction.date) == current_month
        ).first()
        
        if not exists:
            day = min(sub.day_of_month, 28)
            new_pending = models.Transaction(
                date=today.replace(day=day),
                category=sub.category,
                category_id=sub.category_id,
                item=sub.name,
                personal_amount=sub.amount,
                actual_swipe=sub.amount,
                payment_method=sub.payment_method or "信用卡",
                card_id=sub.card_id,
                status="PENDING_SUB",
                subscription_id=sub.id,
                transaction_type="EXPENSE"
            )
            db.add(new_pending)

    insts = db.query(models.Installment).filter(
        models.Installment.remaining_periods > 0
    ).all()
    
    for inst in insts:
        exists = db.query(models.Transaction).filter(
            models.Transaction.installment_id == inst.id,
            extract('year', models.Transaction.date) == current_year,
            extract('month', models.Transaction.date) == current_month
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
                payment_method=inst.payment_method or "信用卡",
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
    return db.query(models.Subscription).all()

def create_subscription(db: Session, sub: schemas.SubscriptionCreate):
    # 校驗分類
    if sub.category_id:
        cat = db.query(models.Category).filter(models.Category.id == sub.category_id).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid category_id")
        sub.category = cat.name

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
    
    # 校驗與同步分類
    if "category_id" in update_data:
        cat = db.query(models.Category).filter(models.Category.id == update_data["category_id"]).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid category_id")
        update_data["category"] = cat.name

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
    db.delete(db_sub)
    db.commit()
    return {"message": "Subscription deleted"}

# --- 分期管理 (Installment CRUD) ---

def get_installments(db: Session):
    return db.query(models.Installment).all()

def create_installment(db: Session, inst: schemas.InstallmentCreate):
    # 校驗卡片
    if inst.card_id:
        card = db.query(models.CreditCard).filter(models.CreditCard.id == inst.card_id).first()
        if not card:
            raise HTTPException(status_code=400, detail="Invalid card_id")
        if not inst.payment_method or inst.payment_method == "信用卡":
            inst.payment_method = card.name

    db_inst = models.Installment(**inst.model_dump())
    db.add(db_inst)
    db.commit()
    db.refresh(db_inst)
    return db_inst

def update_installment(db: Session, inst_id: int, inst_update: schemas.InstallmentUpdate):
    db_inst = db.query(models.Installment).filter(models.Installment.id == inst_id).first()
    if not db_inst:
        raise HTTPException(status_code=404, detail="Installment not found")
    
    update_data = inst_update.model_dump(exclude_unset=True)
    
    # 校驗卡片
    if "card_id" in update_data and update_data["card_id"]:
        card = db.query(models.CreditCard).filter(models.CreditCard.id == update_data["card_id"]).first()
        if not card:
            raise HTTPException(status_code=400, detail="Invalid card_id")
        if "payment_method" not in update_data:
            update_data["payment_method"] = card.name

    for key, value in update_data.items():
        setattr(db_inst, key, value)
    db.commit()
    db.refresh(db_inst)
    return db_inst

def delete_installment(db: Session, inst_id: int):
    db_inst = db.query(models.Installment).filter(models.Installment.id == inst_id).first()
    if not db_inst:
        raise HTTPException(status_code=404, detail="Installment not found")
    db.delete(db_inst)
    db.commit()
    return {"message": "Installment deleted"}
