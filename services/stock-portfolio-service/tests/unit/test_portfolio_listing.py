from datetime import datetime
from decimal import Decimal


def _seed_transactions(db_session):
    from app.models import portfolio as models

    db_session.add_all(
        [
            models.Transaction(
                symbol="0050",
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
                type=models.TransactionType.BUY,
                quantity=12,
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
                trade_date=datetime(2026, 1, 3, 9, 0),
            ),
        ]
    )
    db_session.commit()


def _seed_dividends(db_session):
    from app.models import portfolio as models

    db_session.add_all(
        [
            models.Dividend(
                symbol="0050",
                amount=Decimal("100.00"),
                ex_dividend_date=datetime(2026, 2, 1, 9, 0),
                received_date=datetime(2026, 2, 10, 9, 0),
            ),
            models.Dividend(
                symbol="0050",
                amount=Decimal("110.00"),
                ex_dividend_date=datetime(2026, 3, 1, 9, 0),
                received_date=datetime(2026, 3, 10, 9, 0),
            ),
            models.Dividend(
                symbol="0056",
                amount=Decimal("50.00"),
                ex_dividend_date=datetime(2026, 4, 1, 9, 0),
                received_date=datetime(2026, 4, 10, 9, 0),
            ),
        ]
    )
    db_session.commit()


def test_get_transactions_supports_default_ordering_pagination_and_symbol_filter(client, db_session):
    _seed_transactions(db_session)

    response = client.get("/api/portfolio/transactions")
    assert response.status_code == 200
    assert [item["symbol"] for item in response.json()] == ["0056", "0050", "0050"]

    paged = client.get("/api/portfolio/transactions", params={"limit": 1, "offset": 1})
    assert paged.status_code == 200
    assert len(paged.json()) == 1
    assert paged.json()[0]["trade_date"].startswith("2026-01-02")

    filtered = client.get("/api/portfolio/transactions", params={"symbol": "0050.tw"})
    assert filtered.status_code == 200
    assert [item["symbol"] for item in filtered.json()] == ["0050", "0050"]


def test_get_dividends_supports_default_ordering_pagination_and_symbol_filter(client, db_session):
    _seed_dividends(db_session)

    response = client.get("/api/portfolio/dividends")
    assert response.status_code == 200
    assert [item["symbol"] for item in response.json()] == ["0056", "0050", "0050"]

    paged = client.get("/api/portfolio/dividends", params={"limit": 1, "offset": 1})
    assert paged.status_code == 200
    assert len(paged.json()) == 1
    assert paged.json()[0]["ex_dividend_date"].startswith("2026-03-01")

    filtered = client.get("/api/portfolio/dividends", params={"symbol": "0050.two"})
    assert filtered.status_code == 200
    assert [item["symbol"] for item in filtered.json()] == ["0050", "0050"]


def test_list_endpoints_reject_out_of_range_pagination(client):
    transaction_response = client.get("/api/portfolio/transactions", params={"limit": 0})
    dividend_response = client.get("/api/portfolio/dividends", params={"offset": -1})

    assert transaction_response.status_code == 422
    assert dividend_response.status_code == 422