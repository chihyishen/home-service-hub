from sqlalchemy.orm import Session
from datetime import date
from .. import models, schemas
from ..tracing import tracer
from fastapi import HTTPException
from typing import Optional

def get_transactions(db: Session, skip: int = 0, limit: int = 100, category: Optional[str] = None):
    with tracer.start_as_current_span("service.get_transactions") as span:
        query = db.query(models.Transaction).filter(models.Transaction.is_deleted == False)
        if category:
            span.set_attribute("filter.category", category)
            query = query.filter(models.Transaction.category == category)
        return query.order_by(models.Transaction.date.desc()).offset(skip).limit(limit).all()

def get_transaction(db: Session, transaction_id: int):
    with tracer.start_as_current_span("service.get_transaction") as span:
        span.set_attribute("transaction.id", transaction_id)
        transaction = db.query(models.Transaction).filter(
            models.Transaction.id == transaction_id, 
            models.Transaction.is_deleted == False
        ).first()
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return transaction

def create_transaction(db: Session, transaction: schemas.TransactionCreate):
    with tracer.start_as_current_span("service.create_transaction") as span:
        span.set_attribute("transaction.item", transaction.item)
        span.set_attribute("transaction.amount", transaction.personal_amount)
        span.set_attribute("transaction.type", transaction.transaction_type)

        # 1. 檢查是否有匹配的 PENDING 項目 (訂閱或分期)
        pending_item = db.query(models.Transaction).filter(
            models.Transaction.status.like("PENDING_%"),
            models.Transaction.item == transaction.item,
            models.Transaction.actual_swipe == transaction.actual_swipe,
            models.Transaction.date >= date.today().replace(day=1),
            models.Transaction.is_deleted == False
        ).first()

        if pending_item:
            span.add_event("matched_pending_item", {"id": pending_item.id})
            # 更新現有 PENDING 項目為 COMPLETED
            for key, value in transaction.model_dump(exclude_unset=True).items():
                setattr(pending_item, key, value)
            pending_item.status = "COMPLETED"
            db.commit()
            db.refresh(pending_item)
            return pending_item

        # 2. 如果沒有匹配，建立新紀錄
        db_transaction = models.Transaction(**transaction.model_dump())
        
        # 自動補齊 card_id (如果有 PaymentRoute 映射)
        if not db_transaction.card_id:
            route = db.query(models.PaymentRoute).filter(
                models.PaymentRoute.method_name == transaction.payment_method
            ).first()
            if route:
                span.set_attribute("payment.auto_linked_card", route.card_id)
                db_transaction.card_id = route.card_id

        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        return db_transaction

def update_transaction(db: Session, transaction_id: int, transaction_update: schemas.TransactionUpdate):
    with tracer.start_as_current_span("service.update_transaction") as span:
        span.set_attribute("transaction.id", transaction_id)
        db_transaction = get_transaction(db, transaction_id)
        update_data = transaction_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_transaction, key, value)
        db.commit()
        db.refresh(db_transaction)
        return db_transaction

def delete_transaction(db: Session, transaction_id: int):
    with tracer.start_as_current_span("service.delete_transaction") as span:
        span.set_attribute("transaction.id", transaction_id)
        db_transaction = get_transaction(db, transaction_id)
        db_transaction.is_deleted = True
        db.commit()
        return {"message": "Transaction soft deleted successfully"}
