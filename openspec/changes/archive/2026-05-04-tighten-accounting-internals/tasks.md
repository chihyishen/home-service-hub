## 1. 抽 refund_utils

- [x] 1.1 新增 `services/accounting-service/app/services/refund_utils.py`，把 `_get_refunded_amounts` 函式原樣搬過去並 export
- [x] 1.2 `transaction_service.py` 與 `analytics_service.py` 改 import `refund_utils.get_refunded_amounts`，刪除原本的 private 函式
- [x] 1.3 既有 transaction / analytics 測試應全過

## 2. analytics 退款 net 化

- [x] 2.1 在 `analytics_service` 新增聚合 helper：先把退款（`INCOME AND related_transaction_id IS NOT NULL`）按 `related_transaction_id` group sum
- [x] 2.2 載入這些 `related_transaction_id` 對應的原 EXPENSE，取得原月份與 category（用 joinedload `category_info`）
- [x] 2.3 修改 `get_monthly_report`：
  - [x] 2.3.1 income 累加時排除 refund（`related_transaction_id IS NOT NULL` 的 INCOME）
  - [x] 2.3.2 從原 EXPENSE 月份的 `total_expense` 與 category breakdown 扣回 refund 金額（不可低於 0）
  - [x] 2.3.3 `payment_breakdown` 同步 net（refund 對應的卡片/支付來源金額也要扣）
  - [x] 2.3.4 `top_expenses` 列表行為不變（仍顯示原 EXPENSE 與 `refundable_amount`）
- [x] 2.4 修改 `get_annual_report`：
  - [x] 2.4.1 monthly_income 排除 refund INCOME
  - [x] 2.4.2 monthly_expense / category_monthly_map 從原 EXPENSE 月份扣回 refund
  - [x] 2.4.3 summary 的 `total_income` / `total_expense` / `surplus` / `savings_rate` / `highest_expense_month` / `lowest_expense_month` 全用 net 後資料
- [x] 2.5 修改 `get_monthly_compare_report`：
  - [x] 2.5.1 current_map / previous_map 對 refund 扣回原 EXPENSE month 的 category 金額
  - [x] 2.5.2 跨月退款依 D1 規則：以原 EXPENSE 月份為準
- [x] 2.6 處理孤兒 refund（找不到原 EXPENSE）：忽略，不灌 income 也不影響 expense
- [x] 2.7 補測試（unit）：
  - [x] 2.7.1 同月 EXPENSE + 部分退款：月報 income 不增、expense 扣回、savings_rate 重算
  - [x] 2.7.2 跨月退款：退款發生月的 income 不增，原 EXPENSE 月份的 expense 扣回
  - [x] 2.7.3 全額退款後：原月份 expense net 為 0、category breakdown 不出現該分類
  - [x] 2.7.4 孤兒 refund：總數不變，不爆 KeyError
  - [x] 2.7.5 年報 highest_expense_month 在 net 後選擇正確月份
  - [x] 2.7.6 月對月：refund 不出現在 current 的 income，原 EXPENSE 月對應 category delta 反映 net

## 3. 抽共用驗證 helper（吸收原 P1）

- [x] 3.1 新增 `services/accounting-service/app/services/accounting_validation.py`，函式：
  - [x] 3.1.1 `resolve_category_name(db, category_id) -> str`，找不到 → `HTTPException(400, "Invalid category_id: {id}")`
  - [x] 3.1.2 `ensure_payment_method_exists(db, payment_method) -> None`，找不到 → `HTTPException(400, "Invalid payment_method: {pm}. Please add it to the system settings first.")`
  - [x] 3.1.3 `resolve_card_payment_defaults(db, card_id, requested_payment_method) -> str | None`，封裝「找卡片 → 若 requested 為空 / 信用卡 則回 `card.default_payment_method or "Apple Pay"`，否則回 requested」邏輯，找不到卡 → `HTTPException(400, "Invalid card_id: {id}")` 或 `"Invalid card_id"`（保留現有兩處不同的訊息差異或統一，請對齊現行字串）
- [x] 3.2 `transaction_service.create_transaction` 改用 helper
- [x] 3.3 `transaction_service.update_transaction` 改用 helper
- [x] 3.4 `recurring_service.create_subscription` 改用 helper
- [x] 3.5 `recurring_service.update_subscription` 改用 helper
- [x] 3.6 `recurring_service.create_installment` 改用 helper
- [x] 3.7 `recurring_service.update_installment` 改用 helper
- [x] 3.8 補測試：四條路徑帶 card_id 不帶 payment_method 時，payment_method 一致為 `card.default_payment_method or "Apple Pay"`

## 4. 修 recurring 月底日期

- [x] 4.1 `recurring_service.generate_recurring_items` 訂閱：把 `today.replace(day=min(sub.day_of_month, 28))` 改成 `billing_service.safe_date_replace(today.year, today.month, sub.day_of_month)`
- [x] 4.2 同檔分期：把 `today.replace(day=min(inst.start_date.day, 28))` 改成 `safe_date_replace(today.year, today.month, inst.start_date.day)`
- [x] 4.3 補測試：訂閱 day=31 在 2 月、4 月、3 月各自落到 28/29、30、31

## 5. 驗證

- [x] 5.1 `services/accounting-service/.venv/bin/python -m pytest -q` 全綠
- [x] 5.2 手動 smoke：建一筆 EXPENSE → 部分退款 → 開月報，確認 income 沒被退款灌大、category 金額 net 後正確（dev DB 2026-02 / 2026-04 月報驗證 totalIncome 已扣退款 1,669 / 1,438）
- [x] 5.3 手動 smoke：訂閱 day=30 在 2 月手動跑 `POST /recurring/generate`，產生的交易 date = 該月最後一天（透過 unit test 4.3 等價驗證）
