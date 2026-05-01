from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas
from ..database import get_db
from ..services import card_service, billing_service

router = APIRouter(prefix="/cards", tags=["Cards"])

@router.get("/usage", response_model=List[schemas.analytics.CardUsageSummary], summary="獲取所有信用卡本期使用狀況")
def get_cards_usage(db: Session = Depends(get_db)):
    from ..services import analytics_service
    return analytics_service.get_card_usage_summary(db)

@router.get("/", response_model=List[schemas.CreditCard], summary="獲取所有信用卡")
def list_cards(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return card_service.get_cards(db, skip=skip, limit=limit)

@router.post("/", response_model=schemas.CreditCard, summary="新增信用卡")
def create_card(card: schemas.CreditCardCreate, db: Session = Depends(get_db)):
    return card_service.create_card(db, card)

@router.get("/{card_id}", response_model=schemas.CreditCard, summary="獲取單張信用卡詳情")
def get_card(card_id: int, db: Session = Depends(get_db)):
    return card_service.get_card(db, card_id)

@router.put("/{card_id}", response_model=schemas.CreditCard, summary="修改信用卡資訊")
def update_card(card_id: int, card_update: schemas.CreditCardUpdate, db: Session = Depends(get_db)):
    return card_service.update_card(db, card_id, card_update)

@router.delete("/{card_id}", summary="刪除信用卡")
def delete_card(card_id: int, db: Session = Depends(get_db)):
    return card_service.delete_card(db, card_id)

@router.get("/{card_id}/status", response_model=schemas.CardStatus, summary="獲取信用卡本期帳單狀態")
def get_card_status(card_id: int, db: Session = Depends(get_db)):
    status = billing_service.get_card_status(db, card_id)
    if not status:
        raise HTTPException(status_code=404, detail="Card not found")
    return status
