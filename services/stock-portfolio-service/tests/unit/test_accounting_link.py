"""股票現金流 → 記帳同步的進入點規則。"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from app.services.accounting_link import amount_of


def test_sell_amount_subtracts_costs():
    # 500 × 11.59 = 5795 − 手續費 8 − 稅 17 = 5770 實收
    sell = SimpleNamespace(type="SELL", quantity=500, price=Decimal("11.59"), fee=Decimal("8"), tax=Decimal("17"))
    assert amount_of(sell) == 5770


def test_manual_buy_and_sell_are_synced(client, fake_accounting):
    buy = {"symbol": "0050", "name": "元大台灣50", "type": "BUY", "quantity": 10, "price": "100.5",
           "fee": "1", "trade_date": "2026-11-18T05:30:00Z"}
    res = client.post("/api/portfolio/transactions", json=buy)
    assert res.status_code == 200, res.text
    assert res.json()["accounting_transaction_id"] is not None
    assert fake_accounting.calls[-1] == ("create", "元大台灣50 買進", 1006)

    sell = {**buy, "type": "SELL", "quantity": 5, "price": "101", "fee": "1", "tax": "1"}
    assert client.post("/api/portfolio/transactions", json=sell).status_code == 200
    assert fake_accounting.calls[-1] == ("create", "元大台灣50 賣出", 503)


def test_manual_dividend_synced_with_received_date(client, fake_accounting):
    body = {"symbol": "00919", "amount": "2263.70", "ex_dividend_date": "2026-09-15T00:00:00Z",
            "received_date": "2026-10-15T00:00:00Z"}
    res = client.post("/api/portfolio/dividends", json=body)
    assert res.status_code == 200, res.text
    assert fake_accounting.calls[-1] == ("create_dividend", "00919 配息", 2264)


def test_auto_dividend_waits_for_received_date(client, db_session, fake_accounting):
    from app.models import portfolio as models

    div = models.Dividend(symbol="0050", amount=Decimal("776"), ex_dividend_date=datetime(2026, 7, 20, tzinfo=UTC),
                          source="auto:TWSE_TWT48U")
    db_session.add(div)
    db_session.commit()
    assert fake_accounting.calls == []  # 自動入帳不記帳

    body = {"symbol": "0050", "amount": "776", "ex_dividend_date": "2026-07-20T00:00:00Z"}
    client.put(f"/api/portfolio/dividends/{div.id}", json=body)  # 沒填入帳日：仍不記帳
    assert fake_accounting.calls == []

    client.put(f"/api/portfolio/dividends/{div.id}", json={**body, "received_date": "2026-08-14T00:00:00Z"})
    assert fake_accounting.calls[-1] == ("create_dividend", "0050 配息", 776)
    client.delete(f"/api/portfolio/dividends/{div.id}")
    assert fake_accounting.calls[-1][0] == "remove"
