from sqlalchemy.orm import Session, joinedload
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
                paid_amount=sub.amount,
                transaction_amount=sub.amount,
                payment_method=sub.payment_method or "信用卡",
                card_id=sub.card_id,
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
                paid_amount=inst.monthly_amount,
                transaction_amount=inst.monthly_amount,
                payment_method=inst.payment_method or "信用卡",
                card_id=inst.card_id,
                installment_id=inst.id,
                transaction_type="EXPENSE"
            )
            db.add(new_pending)
            inst.remaining_periods -= 1

    db.commit()

# --- 訂閱管理 (Subscription CRUD) ---

def get_subscriptions(db: Session):
    subs = db.query(models.Subscription).options(joinedload(models.Subscription.card)).all()
    for s in subs:
        if s.card:
            s.card_name = s.card.name
    return subs

def create_subscription(db: Session, sub: schemas.SubscriptionCreate):
    # 校驗分類
    if sub.category_id:
        cat = db.query(models.Category).filter(models.Category.id == sub.category_id).first()
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid category_id")
        sub.category = cat.name
    
    # 校驗付款工具
    if sub.payment_method:
        pm_exists = db.query(models.PaymentMethod).filter(models.PaymentMethod.name == sub.payment_method).first()
        if not pm_exists:
            raise HTTPException(status_code=400, detail=f"Invalid payment_method: {sub.payment_method}")
    
    # 校驗卡片
    if sub.card_id:
        card = db.query(models.CreditCard).filter(models.CreditCard.id == sub.card_id).first()
        if not card:
            raise HTTPException(status_code=400, detail="Invalid card_id")
        if not sub.payment_method or sub.payment_method == "信用卡":
            sub.payment_method = card.default_payment_method or "Apple Pay"

    db_sub = models.Subscription(**sub.model_dump())
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    
    if db_sub.card:
        db_sub.card_name = db_sub.card.name
        
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

    # 校驗付款工具
    if "payment_method" in update_data and update_data["payment_method"]:
        pm_exists = db.query(models.PaymentMethod).filter(models.PaymentMethod.name == update_data["payment_method"]).first()
        if not pm_exists:
            raise HTTPException(status_code=400, detail=f"Invalid payment_method: {update_data['payment_method']}")

    # 校驗卡片
    if "card_id" in update_data and update_data["card_id"]:
        card = db.query(models.CreditCard).filter(models.CreditCard.id == update_data["card_id"]).first()
        if not card:
            raise HTTPException(status_code=400, detail="Invalid card_id")
        if "payment_method" not in update_data or update_data["payment_method"] == "信用卡":
            update_data["payment_method"] = card.default_payment_method or "Apple Pay"

    for key, value in update_data.items():
        setattr(db_sub, key, value)
    db.commit()
    db.refresh(db_sub)
    
    if db_sub.card:
        db_sub.card_name = db_sub.card.name
        
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
    insts = db.query(models.Installment).options(joinedload(models.Installment.card)).all()
    for i in insts:
        if i.card:
            i.card_name = i.card.name
    return insts


def _get_installment_or_404(db: Session, inst_id: int):
    db_inst = db.query(models.Installment).filter(models.Installment.id == inst_id).first()
    if not db_inst:
        raise HTTPException(status_code=404, detail="Installment not found")
    return db_inst

def create_installment(db: Session, inst: schemas.InstallmentCreate):
    # 校驗付款工具
    if inst.payment_method:
        pm_exists = db.query(models.PaymentMethod).filter(models.PaymentMethod.name == inst.payment_method).first()
        if not pm_exists:
            raise HTTPException(status_code=400, detail=f"Invalid payment_method: {inst.payment_method}")

    # 校驗卡片
    if inst.card_id:
        card = db.query(models.CreditCard).filter(models.CreditCard.id == inst.card_id).first()
        if not card:
            raise HTTPException(status_code=400, detail="Invalid card_id")
        if not inst.payment_method or inst.payment_method == "信用卡":
            inst.payment_method = card.default_payment_method or "Apple Pay"

    db_inst = models.Installment(**inst.model_dump())
    db.add(db_inst)
    db.commit()
    db.refresh(db_inst)
    
    if db_inst.card:
        db_inst.card_name = db_inst.card.name
        
    return db_inst

def update_installment(db: Session, inst_id: int, inst_update: schemas.InstallmentUpdate):
    db_inst = _get_installment_or_404(db, inst_id)
    
    update_data = inst_update.model_dump(exclude_unset=True)
    
    # 校驗付款工具
    if "payment_method" in update_data and update_data["payment_method"]:
        pm_exists = db.query(models.PaymentMethod).filter(models.PaymentMethod.name == update_data["payment_method"]).first()
        if not pm_exists:
            raise HTTPException(status_code=400, detail=f"Invalid payment_method: {update_data['payment_method']}")

    # 校驗卡片
    if "card_id" in update_data and update_data["card_id"]:
        card = db.query(models.CreditCard).filter(models.CreditCard.id == update_data["card_id"]).first()
        if not card:
            raise HTTPException(status_code=400, detail="Invalid card_id")
        if "payment_method" not in update_data or update_data["payment_method"] == "信用卡":
            update_data["payment_method"] = card.default_payment_method or "Apple Pay"

    for key, value in update_data.items():
        setattr(db_inst, key, value)
    db.commit()
    db.refresh(db_inst)
    
    if db_inst.card:
        db_inst.card_name = db_inst.card.name
        
    return db_inst

def delete_installment(db: Session, inst_id: int):
    db_inst = _get_installment_or_404(db, inst_id)

    if int(db_inst.remaining_periods or 0) > 0:
        raise HTTPException(status_code=400, detail="Only completed installments can be deleted")

    db.query(models.Transaction).filter(models.Transaction.installment_id == inst_id).update(
        {models.Transaction.installment_id: None},
        synchronize_session=False,
    )
    db.delete(db_inst)
    db.commit()
    return {"message": "Installment deleted"}
