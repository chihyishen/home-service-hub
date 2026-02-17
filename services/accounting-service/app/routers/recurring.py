from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas
from ..database import get_db
from ..services import recurring_service

router = APIRouter(prefix="/recurring", tags=["Recurring"])

@router.post("/generate", summary="手動觸發定期項目生成")
def trigger_recurring_generation(db: Session = Depends(get_db)):
    recurring_service.generate_recurring_items(db)
    return {"message": "Recurring items generated"}

# --- Subscriptions API ---

@router.get("/subscriptions", response_model=List[schemas.Subscription], summary="獲取所有訂閱項目")
def list_subscriptions(db: Session = Depends(get_db)):
    return recurring_service.get_subscriptions(db)

@router.post("/subscriptions", response_model=schemas.Subscription, summary="新增訂閱項目")
def create_subscription(sub: schemas.SubscriptionCreate, db: Session = Depends(get_db)):
    return recurring_service.create_subscription(db, sub)

@router.put("/subscriptions/{sub_id}", response_model=schemas.Subscription, summary="修改訂閱項目")
def update_subscription(sub_id: int, sub_update: schemas.SubscriptionUpdate, db: Session = Depends(get_db)):
    return recurring_service.update_subscription(db, sub_id, sub_update)

@router.patch("/subscriptions/{sub_id}/toggle", response_model=schemas.Subscription, summary="切換訂閱啟用狀態")
def toggle_subscription(sub_id: int, db: Session = Depends(get_db)):
    return recurring_service.toggle_subscription_active(db, sub_id)

@router.delete("/subscriptions/{sub_id}", summary="軟刪除訂閱項目")
def delete_subscription(sub_id: int, db: Session = Depends(get_db)):
    return recurring_service.delete_subscription(db, sub_id)

# --- Installments API ---

@router.get("/installments", response_model=List[schemas.Installment], summary="獲取所有分期項目")
def list_installments(db: Session = Depends(get_db)):
    return recurring_service.get_installments(db)

@router.post("/installments", response_model=schemas.Installment, summary="新增分期項目")
def create_installment(inst: schemas.InstallmentCreate, db: Session = Depends(get_db)):
    return recurring_service.create_installment(db, inst)

@router.put("/installments/{inst_id}", response_model=schemas.Installment, summary="修改分期項目")
def update_installment(inst_id: int, inst_update: schemas.InstallmentUpdate, db: Session = Depends(get_db)):
    return recurring_service.update_installment(db, inst_id, inst_update)

@router.delete("/installments/{inst_id}", summary="軟刪除分期項目")
def delete_installment(inst_id: int, db: Session = Depends(get_db)):
    return recurring_service.delete_installment(db, inst_id)
