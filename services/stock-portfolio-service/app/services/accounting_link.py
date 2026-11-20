"""把股票現金流同步成記帳服務的收支（記帳是使用者的現金流帳）。

- 買進 / 定期定額 → 支出；賣出、股利 → 收入；分類一律「投資」、付款「現金」。
- 交易金額 = 成交價金無條件捨去到整數（台股交割慣例），買進加、賣出減手續費與稅。
- 只同步使用者在 App 內建立的交易；CSV／券商歷史匯入不同步，以免與手記重複。
- 記帳服務掛掉時不讓股票資料寫入失敗：失敗的新增／修改／刪除進 accounting_retries，
  每日 retry_pending 補送；新增帶 externalRef，逾時但其實成功的那筆重送也不會重複記帳。
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

import requests
from sqlalchemy.orm import Session, object_session

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


def _ref(kind: str, source_id: int) -> str:
    """記帳端的冪等鍵：同一筆來源重送只會有一筆記帳。"""
    return f"portfolio:{kind}:{source_id}"


def _create(*, date: str, amount: int, kind: str, item: str, note: str, ref: str) -> int | None:
    try:
        category_id = _category_id()
        if category_id is None:
            logger.warning("accounting_link.category_missing", extra={"category": CATEGORY_NAME})
            return None
        body = {
            "date": date, "transactionAmount": amount, "paidAmount": amount, "transactionType": kind,
            "categoryId": category_id, "item": item, "paymentMethod": PAYMENT_METHOD, "note": note,
            "externalRef": ref,
        }
        resp = requests.post(f"{_BASE}/transactions", json=body, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["id"]
    except requests.RequestException as exc:
        logger.warning("accounting_link.create_failed", extra={"error": str(exc), "ref": ref})
        return None


def _update(accounting_id: int, *, date: str, amount: int, kind: str) -> bool:
    body = {"date": date, "transactionAmount": amount, "paidAmount": amount, "transactionType": kind}
    try:
        requests.put(f"{_BASE}/transactions/{accounting_id}", json=body, timeout=_TIMEOUT).raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.warning("accounting_link.sync_failed", extra={"error": str(exc), "accounting_id": accounting_id})
        return False


def _delete(accounting_id: int) -> bool:
    try:
        resp = requests.delete(f"{_BASE}/transactions/{accounting_id}", timeout=_TIMEOUT)
        if resp.status_code != 404:  # 已經不在就算刪掉了
            resp.raise_for_status()
        return True
    except requests.RequestException as exc:
        logger.warning("accounting_link.remove_failed", extra={"error": str(exc), "accounting_id": accounting_id})
        return False


def _enqueue(db: Session, kind: str, action: str, *, source_id=None, accounting_id=None, item=None) -> None:
    """失敗的同步留給每日 retry_pending 補送；早報會看到未補完的筆數。"""
    from ..models.accounting_retry import AccountingRetry

    db.add(AccountingRetry(kind=kind, action=action, source_id=source_id, accounting_id=accounting_id, item=item))
    db.commit()


def remove(accounting_id: int | None, db: Session) -> None:
    if accounting_id and not _delete(accounting_id):
        _enqueue(db, "txn", "delete", accounting_id=accounting_id)


# ---------------------------------------------------------------- transactions

def _txn_fields(txn) -> dict:
    return {"date": _tw_date(txn.trade_date), "amount": amount_of(txn), "kind": "INCOME" if _is_sell(txn) else "EXPENSE"}


def _create_txn(txn, label: str) -> int | None:
    return _create(**_txn_fields(txn), item=label, note="股票交易自動同步", ref=_ref("txn", txn.id))


def create_for(txn, label: str) -> int | None:
    """label 是完整品名，例如「元大台灣50 買進」。"""
    accounting_id = _create_txn(txn, label)
    if accounting_id is None:
        _enqueue(object_session(txn), "txn", "create", source_id=txn.id, item=label)
    return accounting_id


def sync(txn) -> None:
    if txn.accounting_transaction_id and not _update(txn.accounting_transaction_id, **_txn_fields(txn)):
        _enqueue(object_session(txn), "txn", "update", source_id=txn.id)


def trade_label(name: str, txn) -> str:
    return f"{name} {'賣出' if _is_sell(txn) else '買進'}"


# ---------------------------------------------------------------- dividends

def _dividend_fields(div) -> dict:
    return {"date": _tw_date(div.received_date), "amount": dividend_amount_of(div), "kind": "INCOME"}


def _dividend_syncable(div) -> bool:
    return div.received_date is not None and dividend_amount_of(div) >= 1


def _create_dividend(div, item: str) -> int | None:
    return _create(**_dividend_fields(div), item=item, note="股利自動同步", ref=_ref("dividend", div.id))


def create_for_dividend(div, name: str) -> int | None:
    if not _dividend_syncable(div):
        return None
    item = f"{name} 配息"
    accounting_id = _create_dividend(div, item)
    if accounting_id is None:
        _enqueue(object_session(div), "dividend", "create", source_id=div.id, item=item)
    return accounting_id


def sync_dividend(div) -> None:
    if not (div.accounting_transaction_id and div.received_date is not None):
        return
    if not _update(div.accounting_transaction_id, **_dividend_fields(div)):
        _enqueue(object_session(div), "dividend", "update", source_id=div.id)


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


# ---------------------------------------------------------------- retry (每日排程)

def _retry_one(db: Session, job) -> bool:
    """補送一筆；回傳 True 代表完成（含來源已刪、已連動等不必再做的情況）。"""
    from ..models import portfolio as models

    if job.action == "delete":
        return _delete(job.accounting_id)
    source = db.get(models.Transaction if job.kind == "txn" else models.Dividend, job.source_id)
    if source is None:
        # ponytail: 來源已刪；若當初 POST 其實成功只是逾時，記帳端會留一筆，靠 externalRef 可人工查到
        return True
    if job.action == "update":
        if not source.accounting_transaction_id:
            return True  # 還沒連動，交給 create 那筆
        fields = _txn_fields(source) if job.kind == "txn" else _dividend_fields(source)
        return _update(source.accounting_transaction_id, **fields)
    # create
    if source.accounting_transaction_id or (job.kind == "dividend" and not _dividend_syncable(source)):
        return True
    create = _create_txn if job.kind == "txn" else _create_dividend
    accounting_id = create(source, job.item)
    if accounting_id is None:
        return False
    source.accounting_transaction_id = accounting_id
    return True


def retry_pending(db: Session) -> dict:
    from ..models.accounting_retry import AccountingRetry

    done = remaining = 0
    for job in db.query(AccountingRetry).order_by(AccountingRetry.id).all():
        if _retry_one(db, job):
            db.delete(job)
            done += 1
        else:
            remaining += 1
        db.commit()
    return {"retried": done, "remaining": remaining}
