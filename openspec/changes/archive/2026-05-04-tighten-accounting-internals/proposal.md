## Why

Accounting service 第二輪掃描（2026-05-04，docs/accounting-service-improvements.md F1–F4）發現四個獨立但都屬於「內部一致性」的問題，做完後 API contract 完全不變：

1. 退款交易被建成 `INCOME` 並複製 EXPENSE 的 category，導致月報 / 年報的 `total_income`、`savings_rate`、category breakdown 全部把退款當收入計算，數字失真。
2. `_get_refunded_amounts` 在 `transaction_service.py` 與 `analytics_service.py` 完全重複實作。
3. category / payment_method / card 的校驗與 fallback 邏輯在 `transaction_service` 與 `recurring_service` 重複 6 處（create/update × transaction/subscription/installment），任一漏改就漂移。
4. `recurring_service.generate_recurring_items` 對訂閱與分期的扣款日一律 `min(day, 28)`，把 30 / 31 號訂閱永遠強壓成 28 號，與 `billing_service.safe_date_replace` 已具備的真月底邏輯不一致。

## What Changes

- **退款不再汙染 income**：analytics 聚合時，視 `transaction_type = INCOME AND related_transaction_id IS NOT NULL` 為「退款抵減」而非收入；從 `total_income` 排除，從原 EXPENSE 的對應月份 `total_expense` 與 category 月度金額扣回（net expense）。月報、年報、月對月、top expenses 行為一致。
- **抽 `_get_refunded_amounts`** 到 `app/services/refund_utils.py`，原有兩處改 import；行為與簽名不變。
- **新增 `app/services/accounting_validation.py`**，提供：
  - `resolve_category_name(db, category_id) -> str`
  - `ensure_payment_method_exists(db, payment_method) -> None`
  - `resolve_card_payment_defaults(db, card_id, requested_payment_method) -> str | None`
  - 6 處 service 路徑改為呼叫 helper。HTTPException status / detail 字串維持不變，避免前端需要跟著動。
- **修 recurring 扣款日**：`generate_recurring_items` 改用 `billing_service.safe_date_replace(year, month, day)`，2 月、4 月等短月自動取最後一天。

## Capabilities

### Modified Capabilities

- `accounting-data-integrity`：補強退款計算、共用驗證 helper、recurring 日期解析的不變式。

## Impact

- **Code**:
  - `services/accounting-service/app/services/analytics_service.py`
  - `services/accounting-service/app/services/transaction_service.py`
  - `services/accounting-service/app/services/recurring_service.py`
  - `services/accounting-service/app/services/refund_utils.py`（新增）
  - `services/accounting-service/app/services/accounting_validation.py`（新增）
  - `services/accounting-service/tests/integration/test_transactions.py`
  - `services/accounting-service/tests/integration/test_recurring_api.py`
  - `services/accounting-service/tests/unit/test_analytics_logic.py`
- **API contract**: 不變。`refund_amount`、`refundable_amount`、`payment_method` validation status 與 detail 全部維持。
- **Frontend**: 不需改動；月報的 income/expense 數字會變得更精準（owner 接受）。
- **Risk**:
  - F1a 是語意改變：使用者打開退款後的月報會看到 `total_income` 變小、`total_expense` net 後的 category breakdown 數字下降。需在 release notes 註明。
  - 其他三項（F2/F3/F4）為純內部 refactor / bug fix，風險低。
