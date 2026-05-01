from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db

router = APIRouter(prefix="/payment-methods", tags=["Payment Methods"])

@router.get("/", response_model=List[schemas.payment_method.PaymentMethod])
def list_payment_methods(db: Session = Depends(get_db)):
    return db.query(models.payment_method.PaymentMethod).all()

@router.post("/", response_model=schemas.payment_method.PaymentMethod)
def create_payment_method(pm: schemas.payment_method.PaymentMethodCreate, db: Session = Depends(get_db)):
    db_pm = models.payment_method.PaymentMethod(**pm.model_dump())
    db.add(db_pm)
    try:
        db.commit()
        db.refresh(db_pm)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="支付方式名稱已存在")
    return db_pm

@router.put("/{pm_id}", response_model=schemas.payment_method.PaymentMethod)
def update_payment_method(pm_id: int, pm: schemas.payment_method.PaymentMethodUpdate, db: Session = Depends(get_db)):
    db_pm = db.query(models.payment_method.PaymentMethod).filter(
        models.payment_method.PaymentMethod.id == pm_id
    ).first()
    if not db_pm:
        raise HTTPException(status_code=404, detail="找不到支付方式")
    
    update_data = pm.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_pm, key, value)
    
    try:
        db.commit()
        db.refresh(db_pm)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="更新失敗，名稱可能已存在")
    return db_pm

@router.delete("/{pm_id}", summary="刪除支付方式")
def delete_payment_method(pm_id: int, db: Session = Depends(get_db)):
    db_pm = db.query(models.payment_method.PaymentMethod).filter(
        models.payment_method.PaymentMethod.id == pm_id
    ).first()
    if not db_pm:
        raise HTTPException(status_code=404, detail="找不到支付方式")
    db.delete(db_pm)
    db.commit()
    return {"message": "Success"}
