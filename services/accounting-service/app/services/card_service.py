from sqlalchemy.orm import Session
from .. import models, schemas
from fastapi import HTTPException

def get_cards(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.CreditCard).filter(models.CreditCard.is_deleted == False).offset(skip).limit(limit).all()

def get_card(db: Session, card_id: int):
    card = db.query(models.CreditCard).filter(models.CreditCard.id == card_id, models.CreditCard.is_deleted == False).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card

def create_card(db: Session, card: schemas.CreditCardCreate):
    db_card = models.CreditCard(**card.model_dump())
    db.add(db_card)
    db.commit()
    db.refresh(db_card)
    return db_card

def update_card(db: Session, card_id: int, card_update: schemas.CreditCardUpdate):
    db_card = get_card(db, card_id)
    update_data = card_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_card, key, value)
    db.commit()
    db.refresh(db_card)
    return db_card

def delete_card(db: Session, card_id: int):
    db_card = get_card(db, card_id)
    db_card.is_deleted = True
    db.commit()
    return {"message": "Card soft deleted successfully"}
