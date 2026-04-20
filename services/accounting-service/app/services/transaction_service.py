from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import date, timedelta
from .. import models, schemas
from shared_lib import get_tracer
tracer = get_tracer("accounting-service")
from fastapi import HTTPException
from typing import Optional

VALID_TRANSACTION_TYPES = {"EXPENSE", "INCOME"}
VALID_DATE_PRESETS = {"today", "yesterday", "this_month"}


def _resolve_date_preset(date_preset: str) -> tuple[date, date]:
    today = date.today()

    if date_preset == "today":
        return today, today
    if date_preset == "yesterday":
        yesterday = today - timedelta(days=1)
        return yesterday, yesterday
    if date_preset == "this_month":
        month_start = today.replace(day=1)
        return month_start, today

    raise HTTPException(status_code=400, detail=f"Unsupported date_preset: {date_preset}")


def get_transactions(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    date_preset: Optional[str] = None,
    transaction_type: Optional[str] = None,
    exclude_subscription: bool = False,
    exclude_installment: bool = False,
    manual_only: bool = False,
    keyword: Optional[str] = None,
):
    with tracer.start_as_current_span("service.get_transactions") as span:
        query = db.query(models.Transaction)

        if manual_only:
            span.set_attribute("filter.manual_only", True)
            exclude_subscription = True
            exclude_installment = True
            if date_preset is None and date_from is None and date_to is None:
                date_preset = "today"
            if transaction_type is None:
                transaction_type = "EXPENSE"

        resolved_date_preset = date_preset.lower() if date_preset else None
        if resolved_date_preset:
            if resolved_date_preset not in VALID_DATE_PRESETS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported date_preset: {date_preset}. Supported values: {sorted(VALID_DATE_PRESETS)}",
                )
            if date_from is None and date_to is None:
                date_from, date_to = _resolve_date_preset(resolved_date_preset)

        if category:
            span.set_attribute("filter.category", category)
            query = query.filter(models.Transaction.category == category)
        if date_from:
            span.set_attribute("filter.date_from", date_from.isoformat())
            query = query.filter(models.Transaction.date >= date_from)
        if date_to:
            span.set_attribute("filter.date_to", date_to.isoformat())
            query = query.filter(models.Transaction.date <= date_to)
        if transaction_type:
            normalized_transaction_type = transaction_type.upper()
            if normalized_transaction_type not in VALID_TRANSACTION_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported transaction_type: {transaction_type}. Supported values: {sorted(VALID_TRANSACTION_TYPES)}",
                )
            span.set_attribute("filter.transaction_type", normalized_transaction_type)
            query = query.filter(models.Transaction.transaction_type == normalized_transaction_type)
        if exclude_subscription:
            span.set_attribute("filter.exclude_subscription", True)
            query = query.filter(models.Transaction.subscription_id.is_(None))
        if exclude_installment:
            span.set_attribute("filter.exclude_installment", True)
            query = query.filter(models.Transaction.installment_id.is_(None))
        if keyword:
            pattern = f"%{keyword.strip()}%"
            if pattern != "%%":
                span.set_attribute("filter.keyword", keyword.strip())
                query = query.filter(
                    or_(
                        models.Transaction.item.ilike(pattern),
                        models.Transaction.note.ilike(pattern),
                    )
                )

        transactions = query.order_by(models.Transaction.date.desc(), models.Transaction.id.desc()).offset(skip).limit(limit).all()
        
        # 顯式填充 card_name 以便 Pydantic 輸出
        for t in transactions:
            if t.card:
                t.card_name = t.card.name
        
        return transactions

def get_transaction(db: Session, transaction_id: int):
    with tracer.start_as_current_span("service.get_transaction") as span:
        span.set_attribute("transaction.id", transaction_id)
        transaction = db.query(models.Transaction).filter(
            models.Transaction.id == transaction_id
        ).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction

def create_transaction(db: Session, transaction: schemas.TransactionCreate):
    with tracer.start_as_current_span("service.create_transaction") as span:
        span.set_attribute("transaction.item", transaction.item)
        span.set_attribute("transaction.amount", transaction.transaction_amount)
        span.set_attribute("transaction.type", transaction.transaction_type)

        # --- 資料校驗與自動同步 ---
        # 1. 校驗分類
        if transaction.category_id:
            cat = db.query(models.Category).filter(models.Category.id == transaction.category_id).first()
            if not cat:
                raise HTTPException(status_code=400, detail=f"Invalid category_id: {transaction.category_id}")
            # 強制同步分類名稱
            transaction.category = cat.name
        elif not transaction.category:
             raise HTTPException(status_code=400, detail="Either category_id or category name must be provided")

        # 2. 校驗付款工具 (必須存在於支付方式字典表中)
        if transaction.payment_method:
            pm_exists = db.query(models.PaymentMethod).filter(models.PaymentMethod.name == transaction.payment_method).first()
            if not pm_exists:
                raise HTTPException(status_code=400, detail=f"Invalid payment_method: {transaction.payment_method}. Please add it to the system settings first.")

        # 3. 校驗卡片
        if transaction.card_id:
            card = db.query(models.CreditCard).filter(models.CreditCard.id == transaction.card_id).first()
            if not card:
                raise HTTPException(status_code=400, detail=f"Invalid card_id: {transaction.card_id}")
            # 如果支付方式是空或預設，使用卡片的預設支付工具
            if not transaction.payment_method or transaction.payment_method == "信用卡":
                transaction.payment_method = card.default_payment_method or "Apple Pay"

        # 1. 建立新紀錄
        db_transaction = models.Transaction(**transaction.model_dump())
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        
        if db_transaction.card:
            db_transaction.card_name = db_transaction.card.name
            
        return db_transaction

def refund_transaction(db: Session, transaction_id: int, refund_amount: float):
    """
    針對一筆現有的支出建立沖銷(退款)紀錄
    """
    with tracer.start_as_current_span("service.refund_transaction") as span:
        original = get_transaction(db, transaction_id)
        
        # 建立一筆 INCOME 交易
        refund_tx = models.Transaction(
            date=date.today(),
            category=original.category,
            category_id=original.category_id,
            item=f"退款: {original.item}",
            paid_amount=refund_amount,
            transaction_amount=refund_amount,
            payment_method=original.payment_method,
            card_id=original.card_id,
            transaction_type="INCOME",
            related_transaction_id=original.id,
            note=f"來自原始交易 ID: {original.id} 的沖銷"
        )
        
        db.add(refund_tx)
        db.commit()
        db.refresh(refund_tx)
        
        if refund_tx.card:
            refund_tx.card_name = refund_tx.card.name
            
        return refund_tx

def update_transaction(db: Session, transaction_id: int, transaction_update: schemas.TransactionUpdate):
    with tracer.start_as_current_span("service.update_transaction") as span:
        db_transaction = get_transaction(db, transaction_id)
        update_data = transaction_update.model_dump(exclude_unset=True)

        # --- 資料校驗與自動同步 ---
        if "category_id" in update_data:
            cat = db.query(models.Category).filter(models.Category.id == update_data["category_id"]).first()
            if not cat:
                raise HTTPException(status_code=400, detail=f"Invalid category_id: {update_data['category_id']}")
            update_data["category"] = cat.name
        
        if "payment_method" in update_data and update_data["payment_method"]:
            pm_exists = db.query(models.PaymentMethod).filter(models.PaymentMethod.name == update_data["payment_method"]).first()
            if not pm_exists:
                raise HTTPException(status_code=400, detail=f"Invalid payment_method: {update_data['payment_method']}")

        if "card_id" in update_data:
            if update_data["card_id"]:
                card = db.query(models.CreditCard).filter(models.CreditCard.id == update_data["card_id"]).first()
                if not card:
                    raise HTTPException(status_code=400, detail=f"Invalid card_id: {update_data['card_id']}")
                # 如果沒有明確更新支付方式，則同步
                if "payment_method" not in update_data:
                    update_data["payment_method"] = card.name
            else:
                # 如果取消綁定卡片，支付方式若為卡片名稱，則改為現金或保持原樣 (這裡選擇保持原樣由使用者決定)
                pass

        for key, value in update_data.items():
            setattr(db_transaction, key, value)
        db.commit()
        db.refresh(db_transaction)
        
        if db_transaction.card:
            db_transaction.card_name = db_transaction.card.name
            
        return db_transaction

def delete_transaction(db: Session, transaction_id: int):
    with tracer.start_as_current_span("service.delete_transaction") as span:
        db_transaction = get_transaction(db, transaction_id)
        db.delete(db_transaction)
        db.commit()
        return {"message": "Transaction deleted successfully"}
