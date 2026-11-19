"""把定期定額買進同步成記帳服務的一筆支出。

沿用使用者手記的慣例：分類「投資」、付款「現金」、金額 = 含手續費總額。
記帳服務掛掉時只記 log，不讓股票交易失敗；連動欄位留空即可之後補。
"""

from __future__ import annotations

import logging
import os
from datetime import timedelta, timezone
from decimal import ROUND_DOWN, Decimal

import requests

logger = logging.getLogger(__name__)

_BASE = os.getenv("ACCOUNTING_API_URL", "http://127.0.0.1:8000").rstrip("/") + "/api/accounting"
_TW = timezone(timedelta(hours=8))
_TIMEOUT = 5
CATEGORY_NAME = "投資"
PAYMENT_METHOD = "現金"


def amount_of(txn) -> int:
    """實際扣款：成交價金無條件捨去到整數（台股交割慣例）再加手續費與稅。"""
    gross = (Decimal(txn.quantity) * Decimal(txn.price)).to_integral_value(ROUND_DOWN)
    return int(gross + Decimal(txn.fee or 0) + Decimal(txn.tax or 0))


def _payload(txn) -> dict:
    amount = amount_of(txn)
    return {
        "date": txn.trade_date.astimezone(_TW).date().isoformat(),
        "transactionAmount": amount,
        "paidAmount": amount,
    }


def _category_id() -> int | None:
    resp = requests.get(f"{_BASE}/categories", timeout=_TIMEOUT)
    resp.raise_for_status()
    return next((c["id"] for c in resp.json() if c["name"] == CATEGORY_NAME), None)


def create_for(txn, label: str) -> int | None:
    """建立記帳支出並回傳其 id；失敗回傳 None。"""
    try:
        category_id = _category_id()
        if category_id is None:
            logger.warning("accounting_link.category_missing", extra={"category": CATEGORY_NAME})
            return None
        body = {
            **_payload(txn),
            "categoryId": category_id,
            "item": f"{label} 定期定額",
            "paymentMethod": PAYMENT_METHOD,
            "transactionType": "EXPENSE",
            "note": "股票交易自動同步",
        }
        resp = requests.post(f"{_BASE}/transactions", json=body, timeout=_TIMEOUT)
        resp.raise_for_status()
        return resp.json()["id"]
    except requests.RequestException as exc:
        logger.warning("accounting_link.create_failed", extra={"error": str(exc)})
        return None


def sync(txn) -> None:
    """股票交易被修正後，把記帳金額與日期改成一致。"""
    if not txn.accounting_transaction_id:
        return
    try:
        resp = requests.put(
            f"{_BASE}/transactions/{txn.accounting_transaction_id}", json=_payload(txn), timeout=_TIMEOUT
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("accounting_link.sync_failed", extra={"error": str(exc)})


def remove(accounting_transaction_id: int | None) -> None:
    if not accounting_transaction_id:
        return
    try:
        requests.delete(f"{_BASE}/transactions/{accounting_transaction_id}", timeout=_TIMEOUT).raise_for_status()
    except requests.RequestException as exc:
        logger.warning("accounting_link.remove_failed", extra={"error": str(exc)})
