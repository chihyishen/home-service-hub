# Accounting Service 改善與功能規劃

整理 2026-04-30 review、Opus 4.7 分析與目前 owner 決策，作為後續 OpenSpec changes 與實作依據。

## 決策摘要

服務：`services/accounting-service`

技術棧：Python 3.13 / FastAPI / SQLAlchemy / Alembic / PostgreSQL

幣別假設：目前只處理 TWD，金額以整數儲存與回傳；百分比才使用 float。

本輪明確納入：
- 修正信用卡預設付款方式同步問題。
- 報表查詢改為純讀取，不在 GET 報表時自動產生 recurring transactions。
- 移除「軟刪除」文件語意，維持既有硬刪除。
- 補齊 Alembic baseline，讓空 DB 可以可靠建 schema。
- 規劃年度趨勢報表。
- 規劃分類改名與合併流程。

本輪明確不做：
- 預算模組。
- 交易狀態模型，例如 `PENDING/POSTED`。
- CSV / PDF 匯出。
- 立即匯入對帳單；後續可做「對帳單比對」功能。
- 多幣別。

## A. Data Integrity 改善

### A1. 修正信用卡預設付款方式同步

現況：
- 建立交易時，如果帶 `card_id` 且 `payment_method` 為空或 `"信用卡"`，會同步成 `card.default_payment_method`。
- 更新交易時，如果只更新 `card_id`，目前會把 `payment_method` 設成 `card.name`，和建立邏輯不一致。

調整：
- `transaction_service.update_transaction` 改成和 create 一致：預設同步到 `card.default_payment_method or "Apple Pay"`。
- 補測試覆蓋 create / update 兩條路徑。

### A2. 報表查詢移除寫入副作用

現況：
- `analytics_service.get_monthly_report` 會在查詢當月報表前呼叫 `recurring_service.generate_recurring_items(db)`。

問題：
- GET 報表有資料庫寫入副作用，重跑報表、除錯、測試都比較難預期。

調整：
- 月報、月比月、年度趨勢報表都只讀既有 transactions。
- recurring 生成只透過明確操作觸發，例如現有 `POST /api/accounting/recurring/generate`。
- 前端需要預期 recurring 資料時，由使用者操作或既有排程先產生，再查看報表。

### A3. 移除軟刪除語意，對齊硬刪除

現況：
- 部分 router summary 寫「軟刪除」，但 service 實際上是 `db.delete()`。
- model 沒有 `deleted_at` 或 `is_deleted`。

調整：
- 保持目前直接刪除行為。
- 移除 `services/accounting-service/` 中所有「軟刪除 / soft delete」字樣。
- DELETE endpoint 文件統一描述為「刪除」或「永久刪除」。

### A4. Alembic baseline 補強

現況：
- `alembic/versions/aaaa59cad2a5_baseline_from_existing_schema.py` 名稱是 baseline，但內容只 drop 舊欄位，不能從空 DB 建出完整 schema。

風險：
- 新環境、測試資料庫、災難復原時，`alembic upgrade head` 可能無法建立 tables。

調整：
- 補一份真正可從空 DB 建立 accounting schema 的 Alembic baseline 或修正現有 baseline。
- migration 需包含目前 model 所需 tables：`transactions`、`credit_cards`、`categories`、`payment_methods`、`subscriptions`、`installments`。
- 若既有環境已經套過舊 revision，需提供安全升級策略，例如先 stamp 現況或新增 reconcile migration，而不是破壞 production DB。
- 補驗證：在空 PostgreSQL database 上跑 `alembic upgrade head`，確認 tables、FK、unique/index 都存在。

### A5. Refund 防呆

現況：
- `refund_transaction` 可接受任意金額，也沒有阻止對 INCOME 退款。

調整規則：
- `refund_amount` 必須大於 0。
- 來源交易必須是 `EXPENSE`。
- 已退金額 = 所有 `related_transaction_id == original.id` 且 `transaction_type == "INCOME"` 的 `transaction_amount` 加總。
- `已退金額 + refund_amount` 不可大於原始 `transaction_amount`。
- 回傳 transaction 時可補 `refundable_amount`，讓前端可以限制退款輸入。

### A6. 信用卡週期淨額允許負數

現況：
- `billing_service.get_card_cycle_usage` 會用 `max(0.0, current_usage)` 把淨退款情境壓成 0。

調整：
- 回傳真實淨額，允許負數。
- `is_near_limit` / `is_over_limit` 只在正向淨消費下成立。
- UI 可以把負數顯示成「本期淨退款」。

### A7. N+1 查詢消除

調整：
- `transaction_service.get_transactions` 預載 `card` 與 `category_info`。
- `analytics_service` 讀報表需要 card/category 時使用 joinedload。
- `recurring_service.get_subscriptions` / `get_installments` 預載 card。

### A8. 金額型別一致性

目前 schemas 多數已是 int，但實作仍要守住以下規則：
- 金額欄位一律 `int`。
- 百分比欄位一律 `float`。
- service accumulator 用 `0`，避免 JSON 出現 `123.0`。
- 補測試保護月報、卡片 usage、年度趨勢報表的 JSON 金額型別。

## B. 分類改名與合併規劃

現況：
- `Transaction.category` 字串與 `category_id` FK 並存。
- 報表目前主要依賴字串欄位，分類改名後歷史資料可能漂移。

短期調整：
- 報表分類名稱以 `category_info.name` 優先，fallback 到 `Transaction.category`。
- 更新分類名稱時，同步更新 `transactions.category` 中相同 `category_id` 的歷史交易。

合併規劃：
- 新增 category merge 行為，例如 `POST /api/accounting/categories/{source_id}/merge`。
- 合併時將 source category 相關 transactions / subscriptions 的 `category_id` 改到 target category。
- 同步更新 legacy `category` 字串。
- source category 只有在沒有未遷移引用後才刪除。
- 補 dry-run 或 preview 回傳，讓使用者知道會影響幾筆交易與訂閱。

暫不做：
- 這一輪不強制 `TransactionCreate.category_id` 必填，以免破壞目前前端與舊資料輸入流程。
- 這一輪不移除 `Transaction.category` 字串欄位。

## C. 年度趨勢報表

目的：
- 補上目前只有「單月」與「月對月」報表的缺口。
- 提供全年收入、支出、結餘、分類支出趨勢。

API 建議：

```text
GET /api/accounting/transactions/report/annual/{year}
```

Response 概念：

```json
{
  "year": 2026,
  "monthly_trend": [
    {"month": "2026-01", "total_income": 80000, "total_expense": 55000, "surplus": 25000}
  ],
  "category_trend": [
    {"category": "餐飲", "monthly_amounts": [3200, 4100, 0], "total": 45000, "average": 3750}
  ],
  "summary": {
    "total_income": 960000,
    "total_expense": 660000,
    "surplus": 300000,
    "savings_rate": 31.25,
    "highest_expense_month": "2026-08",
    "lowest_expense_month": "2026-02"
  }
}
```

設計重點：
- 已完成年度回傳 12 個月份；當年度則先回傳 year-to-date 月份範圍，尚未發生的月份不先補進回應。
- 年度報表只讀 transactions，不自動產生 recurring transactions。
- 一次撈出該年度資料後在 Python 端 group，避免對 12 個月份各查一次。
- 分類趨勢回完整分類列表，由前端決定 top 5 或其他顯示方式。

## D. 對帳單比對（後續）

目前不做 CSV 匯出或匯入功能，但可以後續規劃「對帳單比對」：
- 匯入銀行 / 信用卡帳單 CSV。
- 與系統 transactions 比對：日期 ± N 天、金額、商家名稱模糊比對。
- 找出漏記、重複登錄、金額不符。
- 不自動寫入，需人工確認後才建立或修正交易。

建議後續獨立開 change：`add-statement-reconciliation`。

## E. 建議 OpenSpec 拆分

1. `improve-accounting-data-integrity`
   - A1–A8。
   - 包含 Alembic baseline 補強。
   - 包含分類改名同步與分類合併規劃。

2. `add-annual-trend-report`
   - 年度趨勢 API。
   - 前端年度趨勢圖。
   - 依賴 data integrity change 的金額型別與分類 join 規則。

3. `add-statement-reconciliation`
   - 後續再開。
   - 對帳單比對，不在本輪實作。
