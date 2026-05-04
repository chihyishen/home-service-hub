from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from datetime import date, timedelta
from .. import models, schemas
from shared_lib import get_tracer
tracer = get_tracer("accounting-service")
from fastapi import HTTPException
from typing import Optional
from .accounting_validation import (
    ensure_category_exists,
    ensure_payment_method_exists,
    resolve_card_payment_defaults,
)
from .refund_utils import get_refunded_amounts

VALID_TRANSACTION_TYPES = {"EXPENSE", "INCOME"}
VALID_DATE_PRESETS = {"today", "yesterday", "this_month"}


def _base_transaction_query(db: Session):
    return db.query(models.Transaction).options(
        joinedload(models.Transaction.card),
        joinedload(models.Transaction.category_info),
    )


def _populate_transaction_display_fields(
    transactions: list[models.Transaction],
    refunded_amounts: dict[int, int] | None = None,
) -> list[models.Transaction]:
    refunded_amounts = refunded_amounts or {}

    for transaction in transactions:
        transaction.card_name = transaction.card.name if transaction.card else None
        if transaction.transaction_type == "EXPENSE":
            original_amount = int(transaction.transaction_amount or 0)
            refunded_amount = refunded_amounts.get(transaction.id, 0)
            transaction.refundable_amount = max(original_amount - refunded_amount, 0)
        else:
            transaction.refundable_amount = 0

    return transactions


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
        query = _base_transaction_query(db)

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
            query = query.join(models.Transaction.category_info).filter(models.Category.name == category)
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
        refunded_amounts = get_refunded_amounts(db, [transaction.id for transaction in transactions])
        return _populate_transaction_display_fields(transactions, refunded_amounts)

def get_transaction(db: Session, transaction_id: int):
    with tracer.start_as_current_span("service.get_transaction") as span:
        span.set_attribute("transaction.id", transaction_id)
        transaction = _base_transaction_query(db).filter(models.Transaction.id == transaction_id).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        refunded_amounts = get_refunded_amounts(db, [transaction.id])
        _populate_transaction_display_fields([transaction], refunded_amounts)
        return transaction

def create_transaction(db: Session, transaction: schemas.TransactionCreate):
    with tracer.start_as_current_span("service.create_transaction") as span:
        span.set_attribute("transaction.item", transaction.item)
        span.set_attribute("transaction.amount", transaction.transaction_amount)
        span.set_attribute("transaction.type", transaction.transaction_type)

        # --- 資料校驗與自動同步 ---
        # 1. 校驗分類
        ensure_category_exists(db, transaction.category_id)

        # 2. 校驗卡片並同步預設付款工具
        if transaction.card_id:
            transaction.payment_method = resolve_card_payment_defaults(
                db,
                transaction.card_id,
                transaction.payment_method,
            )

        # 3. 校驗付款工具 (必須存在於支付方式字典表中)
        ensure_payment_method_exists(db, transaction.payment_method)

        # 1. 建立新紀錄
        db_transaction = models.Transaction(**transaction.model_dump())
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        return get_transaction(db, db_transaction.id)

def refund_transaction(db: Session, transaction_id: int, refund_amount: int):
    """
    針對一筆現有的支出建立沖銷(退款)紀錄
    """
    with tracer.start_as_current_span("service.refund_transaction") as span:
        original = get_transaction(db, transaction_id)

        if refund_amount <= 0:
            raise HTTPException(status_code=400, detail="Refund amount must be greater than 0")

        if original.transaction_type != "EXPENSE":
            raise HTTPException(status_code=400, detail="Only EXPENSE transactions can be refunded")

        refunded_amounts = get_refunded_amounts(db, [original.id])
        refundable_amount = max(int(original.transaction_amount or 0) - refunded_amounts.get(original.id, 0), 0)

        if refundable_amount <= 0:
            raise HTTPException(status_code=400, detail="Transaction has already been fully refunded")

        if refund_amount > refundable_amount:
            raise HTTPException(status_code=400, detail="Refund amount exceeds refundable amount")
        
        # 建立一筆 INCOME 交易
        refund_tx = models.Transaction(
            date=date.today(),
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
        return get_transaction(db, refund_tx.id)

def update_transaction(db: Session, transaction_id: int, transaction_update: schemas.TransactionUpdate):
    with tracer.start_as_current_span("service.update_transaction") as span:
        db_transaction = get_transaction(db, transaction_id)
        update_data = transaction_update.model_dump(exclude_unset=True)

        # --- 資料校驗與自動同步 ---
        if "category_id" in update_data:
            if update_data["category_id"] is None:
                raise HTTPException(status_code=400, detail="category_id cannot be null")
            ensure_category_exists(db, update_data["category_id"])

        if "card_id" in update_data:
            if update_data["card_id"]:
                update_data["payment_method"] = resolve_card_payment_defaults(
                    db,
                    update_data["card_id"],
                    update_data.get("payment_method"),
                )
            else:
                # 如果取消綁定卡片，支付方式若為卡片名稱，則改為現金或保持原樣 (這裡選擇保持原樣由使用者決定)
                pass

        if "payment_method" in update_data and update_data["payment_method"]:
            ensure_payment_method_exists(
                db,
                update_data["payment_method"],
                invalid_detail_template="Invalid payment_method: {payment_method}",
            )

        for key, value in update_data.items():
            setattr(db_transaction, key, value)
        db.commit()
        db.refresh(db_transaction)
        return get_transaction(db, db_transaction.id)

def delete_transaction(db: Session, transaction_id: int):
    with tracer.start_as_current_span("service.delete_transaction") as span:
        db_transaction = get_transaction(db, transaction_id)
        db.delete(db_transaction)
        db.commit()
        return {"message": "Transaction deleted successfully"}
