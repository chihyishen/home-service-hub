from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..services import dividend_event_service
from ..services.portfolio_service import get_active_holdings

router = APIRouter(
    prefix="/api/portfolio",
    tags=["Portfolio"]
)


@router.get("/dividend-events")
def get_dividend_events(
    year: int | None = Query(default=None, ge=1900, le=2999),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Merged dividend / ex-rights events across TWSE and TPEx."""
    active_holdings = get_active_holdings(db)
    held_symbols = set(active_holdings.keys())
    rows = dividend_event_service.fetch_for_holdings(held_symbols, year=year)
    return [
        {
            "symbol": row.symbol,
            "ex_dividend_date": row.ex_dividend_date.isoformat(),
            "cash_dividend": str(row.cash_dividend) if row.cash_dividend is not None else None,
            "stock_dividend": str(row.stock_dividend) if row.stock_dividend is not None else None,
            "source": row.source,
        }
        for row in rows
    ]
