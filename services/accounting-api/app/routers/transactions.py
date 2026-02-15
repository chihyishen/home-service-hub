from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db
from ..services import accounting, billing

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.post("/", response_model=schemas.Transaction)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    return accounting.create_transaction(db=db, transaction=transaction)

@router.get("/", response_model=List[schemas.Transaction])
def read_transactions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Transaction).offset(skip).limit(limit).all()

@router.get("/card-status/{card_id}", response_model=schemas.CardStatus)
def get_card_status(card_id: int, db: Session = Depends(get_db)):
    status = billing.get_card_status(db, card_id)
    if not status:
        raise HTTPException(status_code=404, detail="Card not found")
    return status

@router.post("/generate-recurring")
def trigger_recurring_generation(db: Session = Depends(get_db)):
    accounting.generate_recurring_items(db)
    return {"message": "Recurring items generated"}
