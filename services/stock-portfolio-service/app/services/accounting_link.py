"""把股票現金流同步成記帳服務的收支（記帳是使用者的現金流帳）。

- 買進 / 定期定額 → 支出；賣出、股利 → 收入；分類一律「投資」、付款「現金」。
- 交易金額 = 成交價金無條件捨去到整數（台股交割慣例），買進加、賣出減手續費與稅。
- 只同步使用者在 App 內建立的交易；CSV／券商歷史匯入不同步，以免與手記重複。
- 記帳服務掛掉時只記 log，不讓股票資料寫入失敗；連動欄位留空，之後可補。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

import requests
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_BASE = os.getenv("ACCOUNTING_API_URL", "http://127.0.0.1:8000").rstrip("/") + "/api/accounting"
_TW = timezone(timedelta(hours=8))
_TIMEOUT = 5
CATEGORY_NAME = "投資"
PAYMENT_METHOD = "現金"


# ---------------------------------------------------------------- amounts

def amount_of(txn) -> int:
    """股票交易的實際收付現金（正數）。"""
    gross = (Decimal(txn.quantity) * Decimal(txn.price)).to_integral_value(ROUND_DOWN)
    costs = Decimal(txn.fee or 0) + Decimal(txn.tax or 0)
    return int(gross - costs if _is_sell(txn) else gross + costs)


def dividend_amount_of(div) -> int:
    return int(Decimal(div.amount).to_integral_value(ROUND_HALF_UP))


def _is_sell(txn) -> bool:
    return str(getattr(txn.type, "value", txn.type)) == "SELL"


def _tw_date(value: datetime) -> str:
    return value.astimezone(_TW).date().isoformat()


def display_name(db: Session, symbol: str, name: str | None = None) -> str:
    """記帳品名用的股票名稱：交易自帶 > 歷史交易 > 代號對照表 > 代號。"""
    from ..models import portfolio as models
    from ..models.symbol_map import SymbolMap

    if name:
        return name
    row = (
        db.query(models.Transaction.name)
        .filter(models.Transaction.symbol == symbol, models.Transaction.name.isnot(None))
        .order_by(models.Transaction.trade_date.desc())
        .first()
    ) or db.query(SymbolMap.name).filter(SymbolMap.symbol == symbol).first()
    return row[0] if row else symbol


# ---------------------------------------------------------------- HTTP core

def _category_id() -> int | None:
    resp = requests.get(f"{_BASE}/categories", timeout=_TIMEOUT)
    resp.raise_for_status()
    return next((c["id"] for c in resp.json() if c["name"] == CATEGORY_NAME), None)


def _create(*, date: str, amount: int, kind: str, item: str, note: str) -> int | None:
    try:
        category_id = _category_id()
        if category_id is None:
            logger.warning("accounting_link.category_missing", extra={"category": CATEGORY_NAME})
            return None
        body = {
            "date": date, "transactionAmount": amount, "paidAmount": amount, "transactionType": kind,
            "categoryId": category_id, "item": item, "paymentMethod": PAYMENT_METHOD, "note": note,
        }
        resp = requests.post(f"{_BASE}/transactions", json=body, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["id"]
    except requests.RequestException as exc:
        logger.warning("accounting_link.create_failed", extra={"error": str(exc)})
        return None


def _update(accounting_id: int, *, date: str, amount: int, kind: str) -> None:
    body = {"date": date, "transactionAmount": amount, "paidAmount": amount, "transactionType": kind}
    try:
        requests.put(f"{_BASE}/transactions/{accounting_id}", json=body, timeout=_TIMEOUT).raise_for_status()
    except requests.RequestException as exc:
        logger.warning("accounting_link.sync_failed", extra={"error": str(exc)})


def remove(accounting_id: int | None) -> None:
    if not accounting_id:
        return
    try:
        requests.delete(f"{_BASE}/transactions/{accounting_id}", timeout=_TIMEOUT).raise_for_status()
    except requests.RequestException as exc:
        logger.warning("accounting_link.remove_failed", extra={"error": str(exc)})


# ---------------------------------------------------------------- transactions

def _txn_fields(txn) -> dict:
    return {"date": _tw_date(txn.trade_date), "amount": amount_of(txn), "kind": "INCOME" if _is_sell(txn) else "EXPENSE"}


def create_for(txn, label: str) -> int | None:
    """label 是完整品名，例如「元大台灣50 買進」。"""
    return _create(**_txn_fields(txn), item=label, note="股票交易自動同步")


def sync(txn) -> None:
    if txn.accounting_transaction_id:
        _update(txn.accounting_transaction_id, **_txn_fields(txn))


def trade_label(name: str, txn) -> str:
    return f"{name} {'賣出' if _is_sell(txn) else '買進'}"


# ---------------------------------------------------------------- dividends

def _dividend_fields(div) -> dict:
    return {"date": _tw_date(div.received_date), "amount": dividend_amount_of(div), "kind": "INCOME"}


def create_for_dividend(div, name: str) -> int | None:
    if div.received_date is None or dividend_amount_of(div) < 1:
        return None
    return _create(**_dividend_fields(div), item=f"{name} 配息", note="股利自動同步")


def sync_dividend(div) -> None:
    if div.accounting_transaction_id and div.received_date is not None:
        _update(div.accounting_transaction_id, **_dividend_fields(div))


# ---------------------------------------------------------------- entry points (App 內建立)

def link_new_transaction(db: Session, txn) -> None:
    """使用者在 App 內新增的現股買賣；融券的現金流另計，不同步。"""
    if str(getattr(txn.position_side, "value", txn.position_side)) != "LONG":
        return
    name = display_name(db, txn.symbol, txn.name)
    txn.accounting_transaction_id = create_for(txn, trade_label(name, txn))
    db.commit()
    db.refresh(txn)


def link_dividend(db: Session, div) -> None:
    div.accounting_transaction_id = create_for_dividend(div, display_name(db, div.symbol))
    db.commit()
    db.refresh(div)
