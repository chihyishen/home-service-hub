from sqlalchemy.orm import Session
from .. import models, schemas
from fastapi import HTTPException

def get_payment_routes(db: Session):
    return db.query(models.PaymentRoute).all()

def create_payment_route(db: Session, route: schemas.payment_route.PaymentRouteCreate):
    # Check if method already exists
    existing = db.query(models.PaymentRoute).filter(models.PaymentRoute.method_name == route.method_name).first()
    if existing:
        # Update existing instead of creating new for convenience
        existing.card_id = route.card_id
        db.commit()
        db.refresh(existing)
        return existing
    
    db_route = models.PaymentRoute(**route.model_dump())
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    return db_route

def delete_payment_route(db: Session, route_id: int):
    db_route = db.query(models.PaymentRoute).filter(models.PaymentRoute.id == route_id).first()
    if not db_route:
        raise HTTPException(status_code=404, detail="Payment route not found")
    db.delete(db_route)
    db.commit()
    return {"message": "Payment route deleted"}
