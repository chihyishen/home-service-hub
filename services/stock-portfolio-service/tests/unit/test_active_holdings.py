from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from app.models import portfolio as models
from app.schemas.portfolio import ExDividendRecord
from app.services import portfolio_service


def test_get_active_holdings_uses_same_day_ordering_and_symbol_normalization(db_session):
    db_session.add_all(
        [
            models.Transaction(
                symbol="0050.tw",
                name="元大台灣50",
                type=models.TransactionType.BUY,
                quantity=10,
                price=Decimal("100.00"),
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                trade_date=datetime(2026, 5, 1, 9, 0),
            ),
            models.Transaction(
                symbol="0050",
                name="元大台灣50",
                type=models.TransactionType.SELL,
                quantity=4,
                price=Decimal("101.00"),
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                trade_date=datetime(2026, 5, 1, 9, 0),
            ),
            models.Transaction(
                symbol="0056",
                name="元大高股息",
                type=models.TransactionType.BUY,
                quantity=5,
                price=Decimal("30.00"),
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                trade_date=datetime(2026, 5, 1, 9, 0),
            ),
            models.Transaction(
                symbol="0056",
                name="元大高股息",
                type=models.TransactionType.SELL,
                quantity=5,
                price=Decimal("31.00"),
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                trade_date=datetime(2026, 5, 2, 9, 0),
            ),
        ]
    )
    db_session.commit()

    active_holdings = portfolio_service.get_active_holdings(db_session)

    assert set(active_holdings.keys()) == {"0050"}
    assert active_holdings["0050"]["total_quantity"] == 6


@patch("app.routers.exdividend.fetch_upcoming_exdividends")
@patch("app.services.portfolio.summary.get_stock_quotes")
def test_summary_and_exdividend_use_same_active_symbols(mock_get_quotes, mock_fetch_exdividends, client, db_session):
    db_session.add_all(
        [
            models.Transaction(
                symbol="0050.TW",
                name="元大台灣50",
                type=models.TransactionType.BUY,
                quantity=10,
                price=Decimal("100.00"),
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                trade_date=datetime(2026, 1, 1, 9, 0),
            ),
            models.Transaction(
                symbol="0050",
                name="元大台灣50",
                type=models.TransactionType.SELL,
                quantity=4,
                price=Decimal("101.00"),
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                trade_date=datetime(2026, 1, 2, 9, 0),
            ),
            models.Transaction(
                symbol="0056",
                name="元大高股息",
                type=models.TransactionType.BUY,
                quantity=5,
                price=Decimal("30.00"),
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                trade_date=datetime(2026, 1, 1, 9, 0),
            ),
            models.Transaction(
                symbol="0056",
                name="元大高股息",
                type=models.TransactionType.SELL,
                quantity=5,
                price=Decimal("31.00"),
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                trade_date=datetime(2026, 1, 2, 9, 0),
            ),
            models.Transaction(
                symbol="00919.TWO",
                name="群益台灣精選高息",
                type=models.TransactionType.BUY,
                quantity=3,
                price=Decimal("20.00"),
                fee=Decimal("0.00"),
                tax=Decimal("0.00"),
                trade_date=datetime(2026, 1, 3, 9, 0),
            ),
        ]
    )
    db_session.commit()

    mock_get_quotes.return_value = {
        "0050": {
            "symbol": "0050",
            "name": "元大台灣50",
            "current_price": Decimal("102.00"),
            "yesterday_close": Decimal("101.00"),
            "time": "13:30:00",
        },
        "00919": {
            "symbol": "00919",
            "name": "群益台灣精選高息",
            "current_price": Decimal("21.00"),
            "yesterday_close": Decimal("20.50"),
            "time": "13:30:00",
        },
    }
    mock_fetch_exdividends.side_effect = lambda held_symbols: [
        ExDividendRecord(symbol=symbol, name=symbol) for symbol in sorted(held_symbols)
    ]

    summary = portfolio_service.get_portfolio_summary(db_session)
    response = client.get("/api/portfolio/ex-dividends/upcoming")

    assert response.status_code == 200
    assert {holding.symbol for holding in summary.holdings} == {"0050", "00919"}
    assert {record["symbol"] for record in response.json()} == {"0050", "00919"}