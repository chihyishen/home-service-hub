from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import portfolio as models
from ..schemas.portfolio import ExDividendRecord
from ..services.exdividend_service import fetch_upcoming_exdividends
from ..services.portfolio_service import sanitize_symbol

router = APIRouter(
    prefix="/api/portfolio",
    tags=["Portfolio"]
)


@router.get("/ex-dividends/upcoming", response_model=List[ExDividendRecord])
def get_upcoming_exdividends(db: Session = Depends(get_db)):
    """
    Return upcoming ex-dividend announcements from TWSE for stocks
    currently held in the portfolio (quantity > 0).
    """
    transactions = db.query(models.Transaction).order_by(models.Transaction.trade_date).all()

    holdings_qty: dict = {}
    for t in transactions:
        symbol = sanitize_symbol(t.symbol)
        if t.type == models.TransactionType.BUY:
            holdings_qty[symbol] = holdings_qty.get(symbol, 0) + t.quantity
        elif t.type == models.TransactionType.SELL:
            holdings_qty[symbol] = holdings_qty.get(symbol, 0) - t.quantity

    held_symbols = {s for s, qty in holdings_qty.items() if qty > 0}
    return fetch_upcoming_exdividends(held_symbols)
