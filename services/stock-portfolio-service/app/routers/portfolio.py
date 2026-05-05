from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas import portfolio as schemas
from ..services import portfolio_service
from ..models import portfolio as models

router = APIRouter(
    prefix="/api/portfolio",
    tags=["Portfolio"]
)

@router.get("/summary", response_model=schemas.PortfolioSummary)
def get_summary(db: Session = Depends(get_db)):
    return portfolio_service.get_portfolio_summary(db)

@router.post("/transactions", response_model=schemas.Transaction)
def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    try:
        return portfolio_service.create_transaction(db, transaction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.put("/transactions/{transaction_id}", response_model=schemas.Transaction)
def update_transaction(transaction_id: int, transaction: schemas.TransactionCreate, db: Session = Depends(get_db)):
    try:
        updated = portfolio_service.update_transaction(db, transaction_id, transaction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not updated:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return updated

@router.delete("/transactions/{transaction_id}")
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)):
    success = portfolio_service.delete_transaction(db, transaction_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted"}

@router.get("/transactions", response_model=List[schemas.Transaction])
def get_transactions(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    symbol: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return portfolio_service.list_transactions(db, limit=limit, offset=offset, symbol=symbol)

@router.post("/dividends", response_model=schemas.Dividend)
def create_dividend(dividend: schemas.DividendCreate, db: Session = Depends(get_db)):
    return portfolio_service.create_dividend(db, dividend)

@router.put("/dividends/{dividend_id}", response_model=schemas.Dividend)
def update_dividend(dividend_id: int, dividend: schemas.DividendCreate, db: Session = Depends(get_db)):
    updated = portfolio_service.update_dividend(db, dividend_id, dividend)
    if not updated:
        raise HTTPException(status_code=404, detail="Dividend not found")
    return updated

@router.delete("/dividends/{dividend_id}")
def delete_dividend(dividend_id: int, db: Session = Depends(get_db)):
    success = portfolio_service.delete_dividend(db, dividend_id)
    if not success:
        raise HTTPException(status_code=404, detail="Dividend not found")
    return {"message": "Dividend deleted"}

@router.get("/dividends", response_model=List[schemas.Dividend])
def get_dividends(
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    symbol: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return portfolio_service.list_dividends(db, limit=limit, offset=offset, symbol=symbol)
