"""定期定額：在扣款日（遇非交易日順延）收盤後，以收盤價建立一筆估算買進。

券商實際成交價是盤中零股成交均價，事前無法得知，因此交易標記
``is_estimated``，使用者在券商 App 看到實際成交後手動更正即可。
股數 = floor((扣款金額 - 手續費) / 價格)，與國泰定期定額歷史紀錄吻合。
"""

from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_DOWN, Decimal

from sqlalchemy.orm import Session

from ..models import portfolio as models
from ..models.dca_plan import DcaPlan
from ..models.price_history import PriceHistory
from ..schemas import portfolio as schemas
from . import portfolio_service

logger = logging.getLogger(__name__)

_TW = timezone(timedelta(hours=8))
_TRADE_TIME = time(13, 30)  # 存成台北 13:30，使 UTC 日期與台股交易日一致


def today_tw() -> date:
    return datetime.now(_TW).date()


def target_date(year: int, month: int, day_of_month: int) -> date:
    return date(year, month, min(day_of_month, calendar.monthrange(year, month)[1]))


def _execution_day(db: Session, symbol: str, target: date, today: date) -> PriceHistory | None:
    """target 當天或之後、today 以前的第一個交易日收盤（以 price_history 判定交易日）。"""
    return (
        db.query(PriceHistory)
        .filter(PriceHistory.symbol == symbol, PriceHistory.date >= target, PriceHistory.date <= today)
        .order_by(PriceHistory.date)
        .first()
    )


def run_plan(db: Session, plan: DcaPlan, today: date) -> models.Transaction | None:
    target = target_date(today.year, today.month, plan.day_of_month)
    if today < target or (plan.last_executed_on and plan.last_executed_on >= target):
        return None
    bar = _execution_day(db, plan.symbol, target, today)
    if bar is None:
        return None  # 收盤價尚未進來，下次再跑

    price = Decimal(bar.close).quantize(Decimal("0.01"))
    quantity = int(((Decimal(plan.amount) - Decimal(plan.fee)) / price).to_integral_value(ROUND_DOWN))
    plan.last_executed_on = bar.date
    if quantity <= 0:
        logger.warning("dca.amount_too_small", extra={"symbol": plan.symbol, "price": str(price)})
        db.commit()
        return None

    previous = (
        db.query(models.Transaction.name)
        .filter(models.Transaction.symbol == plan.symbol, models.Transaction.name.isnot(None))
        .order_by(models.Transaction.trade_date.desc())
        .first()
    )
    txn = portfolio_service.create_transaction(
        db,
        schemas.TransactionCreate(
            symbol=plan.symbol,
            name=previous[0] if previous else None,
            type=schemas.TransactionType.BUY,
            quantity=quantity,
            price=price,
            fee=Decimal(plan.fee).quantize(Decimal("0.01")),
            trade_date=datetime.combine(bar.date, _TRADE_TIME, _TW),
        ),
    )
    txn.is_estimated = True
    db.commit()
    db.refresh(txn)
    logger.info("dca.executed", extra={"symbol": plan.symbol, "date": str(bar.date), "quantity": quantity})
    return txn


def run_due(db: Session, today: date) -> list[models.Transaction]:
    created = []
    for plan in db.query(DcaPlan).filter(DcaPlan.active.is_(True)).all():
        txn = run_plan(db, plan, today)
        if txn is not None:
            created.append(txn)
    return created
