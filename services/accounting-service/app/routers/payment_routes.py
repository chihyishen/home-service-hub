from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import schemas, models
from ..database import get_db
from ..services import payment_route_service

router = APIRouter(prefix="/payment-routes", tags=["Payment Routes"])

@router.get("/", response_model=List[schemas.payment_route.PaymentRoute])
def list_payment_routes(db: Session = Depends(get_db)):
    return payment_route_service.get_payment_routes(db)

@router.post("/", response_model=schemas.payment_route.PaymentRoute)
def create_payment_route(route: schemas.payment_route.PaymentRouteCreate, db: Session = Depends(get_db)):
    return payment_route_service.create_payment_route(db, route)

@router.delete("/{id}")
def delete_payment_route(id: int, db: Session = Depends(get_db)):
    return payment_route_service.delete_payment_route(db, id)
