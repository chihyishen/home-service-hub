from datetime import date
from decimal import Decimal

from app.models.dca_plan import DcaPlan
from app.models.price_history import PriceHistory
from app.services import dca_service


def _close(db, d, close):
    db.add(PriceHistory(symbol="0050", date=d, close=Decimal(close), source="TWSE"))


def _plan(db):
    plan = DcaPlan(symbol="0050", amount=2000, day_of_month=25, fee=Decimal("1"))
    db.add(plan)
    db.commit()
    return plan


def test_buys_on_next_trading_day_when_target_is_holiday(db_session):
    # 2026-10-25 Sun, 10-26 holiday → first trading day 10-27
    plan = _plan(db_session)
    _close(db_session, date(2026, 10, 27), "106.45")
    db_session.commit()

    assert dca_service.run_due(db_session, date(2026, 10, 26)) == []
    [txn] = dca_service.run_due(db_session, date(2026, 10, 27))
    assert txn.quantity == 18  # floor(1999 / 106.45)
    assert txn.price == Decimal("106.45")
    assert txn.is_estimated is True
    assert plan.last_executed_on == date(2026, 10, 27)

    # idempotent for the month
    _close(db_session, date(2026, 10, 28), "100")
    db_session.commit()
    assert dca_service.run_due(db_session, date(2026, 10, 28)) == []


def test_waits_for_close_then_catches_up(db_session):
    _plan(db_session)
    assert dca_service.run_due(db_session, date(2026, 8, 25)) == []  # close not in yet
    _close(db_session, date(2026, 8, 25), "103.03")
    db_session.commit()
    [txn] = dca_service.run_due(db_session, date(2026, 8, 26))
    assert txn.quantity == 19


def test_manual_edit_clears_estimated_flag(client, db_session, fake_accounting):
    _plan(db_session)
    _close(db_session, date(2026, 9, 29), "111.30")
    db_session.commit()
    [txn] = dca_service.run_due(db_session, date(2026, 9, 29))

    body = {"symbol": "0050", "type": "BUY", "quantity": 17, "price": "111.68", "fee": "1",
            "trade_date": txn.trade_date.isoformat()}
    res = client.put(f"/api/portfolio/transactions/{txn.id}", json=body)
    assert res.status_code == 200, res.text
    assert res.json()["is_estimated"] is False
    # 建立時同步一筆記帳（17 股 × 111.30 + 1 = 1893），修正後同步、刪除後移除
    assert fake_accounting.calls[0] == ("create", "0050 定期定額", 1893)
    assert fake_accounting.calls[1] == ("sync", txn.accounting_transaction_id)
    assert client.delete(f"/api/portfolio/transactions/{txn.id}").status_code in (200, 204)
    assert fake_accounting.calls[-1] == ("remove", 901)


def test_plan_crud(client):
    res = client.post("/api/portfolio/dca-plans", json={"symbol": "0050.TW", "amount": 2000, "day_of_month": 25})
    assert res.status_code == 200, res.text
    plan = res.json()
    assert plan["symbol"] == "0050" and Decimal(plan["fee"]) == 1
    assert client.get("/api/portfolio/dca-plans").json()[0]["id"] == plan["id"]
    assert client.delete(f"/api/portfolio/dca-plans/{plan['id']}").status_code == 200


def test_skips_month_without_the_day():
    from app.services.dca_service import target_date
    assert target_date(2026, 2, 30) is None
    assert target_date(2026, 3, 30).day == 30


def test_accounting_amount_truncates_trade_value():
    from types import SimpleNamespace

    from app.services.accounting_link import amount_of
    # 17 × 111.68 = 1898.56 → 價金 1898 + 手續費 1 = 1899（與國泰實際扣款一致）
    assert amount_of(SimpleNamespace(type="BUY", quantity=17, price=Decimal("111.68"), fee=Decimal("1"), tax=0)) == 1899
