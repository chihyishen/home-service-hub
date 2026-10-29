import logging
from datetime import date

from fastapi import HTTPException
from sqlalchemy import extract
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from .accounting_validation import (
    ensure_category_exists,
    ensure_payment_method_exists,
    resolve_card_payment_defaults,
)
from .billing_service import safe_date_replace

logger = logging.getLogger(__name__)


def _validate_subscription_values(values: dict):
    if not values["name"] or not values["name"].strip():
        raise HTTPException(status_code=400, detail="項目名稱不可空白")
    if values["amount"] is None or values["amount"] <= 0:
        raise HTTPException(status_code=400, detail="每月金額必須大於 0")
    if values["category_id"] is None:
        raise HTTPException(status_code=400, detail="category_id cannot be null")
    if values["category_id"] <= 0:
        raise HTTPException(status_code=400, detail="分類 ID 必須大於 0")
    if values["sub_type"] not in {"SUBSCRIPTION", "FIXED_EXPENSE"}:
        raise HTTPException(status_code=400, detail="項目類型必須為固定支出或數位訂閱")
    if values["day_of_month"] is None or not 1 <= values["day_of_month"] <= 31:
        raise HTTPException(status_code=400, detail="扣款日必須介於 1 到 31")
    if not values["payment_method"] or not values["payment_method"].strip():
        raise HTTPException(status_code=400, detail="支付方式不可空白")
    if values["active"] is None:
        raise HTTPException(status_code=400, detail="啟用狀態不可為空")
    if values["card_id"] is not None and values["card_id"] <= 0:
        raise HTTPException(status_code=400, detail="信用卡 ID 必須大於 0")


def _validate_installment_values(values: dict):
    if not values["name"] or not values["name"].strip():
        raise HTTPException(status_code=400, detail="分期名稱不可空白")
    if values["total_amount"] is None or values["total_amount"] <= 0:
        raise HTTPException(status_code=400, detail="總金額必須大於 0")
    if values["monthly_amount"] is None or values["monthly_amount"] <= 0:
        raise HTTPException(status_code=400, detail="每期金額必須大於 0")
    if values["monthly_amount"] > values["total_amount"]:
        raise HTTPException(status_code=400, detail="每期金額不可大於總金額")
    if values["total_periods"] is None or values["total_periods"] <= 0:
        raise HTTPException(status_code=400, detail="總期數必須大於 0")
    if values["remaining_periods"] is None or not 0 <= values["remaining_periods"] <= values["total_periods"]:
        raise HTTPException(status_code=400, detail="剩餘期數必須介於 0 至總期數之間")
    if values["start_date"] is None:
        raise HTTPException(status_code=400, detail="開始日期不可為空")
    if not values["payment_method"] or not values["payment_method"].strip():
        raise HTTPException(status_code=400, detail="支付方式不可空白")
    if values["card_id"] is not None and values["card_id"] <= 0:
        raise HTTPException(status_code=400, detail="信用卡 ID 必須大於 0")
    if values["total_amount"] - values["monthly_amount"] * (values["total_periods"] - 1) <= 0:
        raise HTTPException(status_code=400, detail="最後一期金額必須大於 0；請調整每期金額或總金額")


def _get_or_create_installment_category_id(db: Session) -> int:
    category = db.query(models.Category).filter(models.Category.name == "分期付款").first()
    if category:
        return int(category.id)

    category = models.Category(name="分期付款")
    db.add(category)
    db.flush()
    return int(category.id)

# --- 自動化生成邏輯 ---

def generate_recurring_items(db: Session):
    today = date.today()
    current_year = today.year
    current_month = today.month
    
    subs = db.query(models.Subscription).filter(
        models.Subscription.active.is_(True)
    ).order_by(models.Subscription.id).with_for_update().all()
    
    for sub in subs:
        if sub.skipped_month == today.replace(day=1):
            continue
        exists = db.query(models.Transaction).filter(
            models.Transaction.subscription_id == sub.id,
            extract('year', models.Transaction.date) == current_year,
            extract('month', models.Transaction.date) == current_month
        ).first()
        
        if not exists:
            new_pending = models.Transaction(
                date=safe_date_replace(today.year, today.month, sub.day_of_month),
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
    ).order_by(models.Installment.id).with_for_update().all()
    
    for inst in insts:
        # 計算基於 start_date 與當前年份月份的實際期數
        elapsed_months = (current_year - inst.start_date.year) * 12 + (current_month - inst.start_date.month)
        current_period = elapsed_months + 1
        
        if current_period <= 0:
            logger.info("分期付款 %s 尚未到期 (開始日期為 %s)，跳過生成", inst.name, inst.start_date)
            continue
            
        if current_period > inst.total_periods:
            # 已經超出分期總期數，將 remaining_periods 歸零，標記為已結束
            if inst.remaining_periods > 0:
                inst.remaining_periods = 0
                logger.info("分期付款 %s 已超出總期數，自動更新剩餘期數為 0", inst.name)
            continue
            
        exists = db.query(models.Transaction).filter(
            models.Transaction.installment_id == inst.id,
            extract('year', models.Transaction.date) == current_year,
            extract('month', models.Transaction.date) == current_month
        ).first()
        
        if not exists:
            item_name = f"{inst.name} (第 {current_period}/{inst.total_periods} 期)"
            amount = (
                inst.total_amount - inst.monthly_amount * (inst.total_periods - 1)
                if current_period == inst.total_periods
                else inst.monthly_amount
            )
            new_pending = models.Transaction(
                date=safe_date_replace(today.year, today.month, inst.start_date.day),
                category_id=_get_or_create_installment_category_id(db),
                item=item_name,
                paid_amount=amount,
                transaction_amount=amount,
                payment_method=inst.payment_method or "信用卡",
                card_id=inst.card_id,
                installment_id=inst.id,
                transaction_type="EXPENSE"
            )
            db.add(new_pending)
            inst.remaining_periods = inst.total_periods - current_period

    db.commit()

# --- 訂閱管理 (Subscription CRUD) ---

def get_subscriptions(db: Session):
    subs = db.query(models.Subscription).options(
        joinedload(models.Subscription.card),
        joinedload(models.Subscription.category_info),
    ).all()
    for s in subs:
        if s.card:
            s.card_name = s.card.name
    return subs

def create_subscription(db: Session, sub: schemas.SubscriptionCreate):
    _validate_subscription_values(sub.model_dump())

    # 校驗分類
    ensure_category_exists(
        db,
        sub.category_id,
        invalid_detail_template="Invalid category_id",
    )

    # 校驗卡片
    if sub.card_id:
        sub.payment_method = resolve_card_payment_defaults(
            db,
            sub.card_id,
            sub.payment_method,
            invalid_detail_template="Invalid card_id",
        )
    
    # 校驗付款工具
    ensure_payment_method_exists(
        db,
        sub.payment_method,
        invalid_detail_template="Invalid payment_method: {payment_method}",
    )

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

    if "category_id" in update_data and update_data["category_id"] is None:
        raise HTTPException(status_code=400, detail="category_id cannot be null")
    for field, label in (
        ("name", "項目名稱"), ("amount", "每月金額"), ("sub_type", "項目類型"),
        ("payment_method", "支付方式"), ("day_of_month", "扣款日"), ("active", "啟用狀態"),
    ):
        if field in update_data and update_data[field] is None:
            raise HTTPException(status_code=400, detail=f"{label}不可為空")
    
    # 校驗與同步分類
    if "category_id" in update_data:
        ensure_category_exists(
            db,
            update_data["category_id"],
            invalid_detail_template="Invalid category_id",
        )

    # 校驗卡片
    if update_data.get("card_id"):
        update_data["payment_method"] = resolve_card_payment_defaults(
            db,
            update_data["card_id"],
            update_data.get("payment_method"),
            invalid_detail_template="Invalid card_id",
        )

    if update_data.get("payment_method"):
        ensure_payment_method_exists(
            db,
            update_data["payment_method"],
            invalid_detail_template="Invalid payment_method: {payment_method}",
        )

    values = {field: getattr(db_sub, field) for field in (
        "name", "amount", "category_id", "sub_type", "day_of_month", "payment_method", "active", "card_id"
    )}
    values.update(update_data)
    _validate_subscription_values(values)

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


def skip_subscription_current_month(db: Session, sub_id: int):
    db_sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db_sub.skipped_month = date.today().replace(day=1)
    db.commit()
    db.refresh(db_sub)
    return db_sub


def undo_skip_subscription_current_month(db: Session, sub_id: int):
    db_sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db_sub.skipped_month = None
    db.commit()
    db.refresh(db_sub)
    return db_sub

def delete_subscription(db: Session, sub_id: int):
    db_sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id).first()
    if not db_sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.query(models.Transaction).filter(models.Transaction.subscription_id == sub_id).update(
        {models.Transaction.subscription_id: None},
        synchronize_session=False,
    )
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
    _validate_installment_values(inst.model_dump())

    # 校驗卡片
    if inst.card_id:
        inst.payment_method = resolve_card_payment_defaults(
            db,
            inst.card_id,
            inst.payment_method,
            invalid_detail_template="Invalid card_id",
        )

    # 校驗付款工具
    ensure_payment_method_exists(
        db,
        inst.payment_method,
        invalid_detail_template="Invalid payment_method: {payment_method}",
    )

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

    for field, label in (
        ("name", "分期名稱"), ("total_amount", "總金額"), ("monthly_amount", "每期金額"),
        ("payment_method", "支付方式"), ("total_periods", "總期數"),
        ("remaining_periods", "剩餘期數"), ("start_date", "開始日期"),
    ):
        if field in update_data and update_data[field] is None:
            raise HTTPException(status_code=400, detail=f"{label}不可為空")
    
    # 校驗卡片
    if update_data.get("card_id"):
        update_data["payment_method"] = resolve_card_payment_defaults(
            db,
            update_data["card_id"],
            update_data.get("payment_method"),
            invalid_detail_template="Invalid card_id",
        )

    if update_data.get("payment_method"):
        ensure_payment_method_exists(
            db,
            update_data["payment_method"],
            invalid_detail_template="Invalid payment_method: {payment_method}",
        )

    values = {field: getattr(db_inst, field) for field in (
        "name", "total_amount", "monthly_amount", "payment_method", "total_periods", "remaining_periods", "start_date", "card_id"
    )}
    values.update(update_data)
    _validate_installment_values(values)

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
