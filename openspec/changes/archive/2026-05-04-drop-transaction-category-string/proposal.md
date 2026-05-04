## Why

`Transaction` 與 `Subscription` 同時存 `category` 字串欄位與 `category_id` FK，兩個欄位透過散落多處的同步寫入維持一致：
- `transaction_service.create_transaction` / `update_transaction` 在 set `category_id` 時順便寫 `category` 字串。
- `recurring_service` 在訂閱/分期路徑做相同雙寫。
- `categories.py::_sync_category_name_references` 在分類改名時 SQL update 所有引用列的 `category` 字串。
- `merge_categories` 在合併時要同步寫 `category_id` 與 `category` 字串。

這是 dual-write 風險。任一路徑漏寫就會漂移；前一輪 `improve-accounting-data-integrity` 為此加了同步 + fallback，沒拔掉根本問題。

owner 在 2026-05-04 review 中決議：「我要免除雙寫風險，這是不該存在的」、「資料面可以使用 SQL 就用 SQL 處理」。

## What Changes

- **DB schema (Alembic upgrade，純 SQL backfill)**
  - Backfill `transactions.category_id` for rows where `category_id IS NULL AND category IS NOT NULL`：依 `category` 字串對 `categories.name` 做 join；對 `categories` 沒有的 distinct 字串先 `INSERT INTO categories(name) VALUES (...)` 再回填。
  - 同步 backfill `subscriptions.category_id`。
  - 加 `NOT NULL` constraint 到 `transactions.category_id`、`subscriptions.category_id`。
  - Drop `transactions.category` 與 `subscriptions.category` 欄位。
- **Models**：移除 `Transaction.category`、`Subscription.category` columns。
- **Schemas（API breaking）**：
  - `TransactionCreate.category_id`、`TransactionUpdate.category_id` 改為必填（create）/ 不再帶 legacy `category` 字串。
  - `SubscriptionCreate.category_id` 必填。
  - 響應端新增 / 保留 `category_name: str`（從 relationship 計算）給前端顯示。
- **Service 層**：
  - `transaction_service` / `recurring_service` 移除所有 `obj.category = cat.name` 同步寫入。
  - `analytics_service._resolve_category_name` 直接讀 `category_info.name`（不再 fallback 到 `transaction.category` 字串）。
  - `categories.py::_sync_category_name_references` 與 merge endpoint 中 update legacy 字串的 SQL 全部刪除。
- **Frontend audit**：
  - 所有讀 `transaction.category`（字串）的地方改讀 `transaction.category_name` 或 `transaction.category_info?.name`。
  - 送出 payload 一律帶 `category_id`，移除送 `category` 字串的路徑。

## Capabilities

### Modified Capabilities

- `accounting-data-integrity`：
  - 改寫「分類改名同步 legacy category 字串」要求（legacy 字串移除後不再需要同步）。
  - 改寫「分類合併」要求（apply 時不再需要同步 legacy 字串）。
- `accounting-annual-report` / `accounting-monthly-report`（如 spec 已存在）：分類名稱來源固定為 `category_info.name`，無 fallback。

## Impact

- **Code**:
  - `services/accounting-service/app/models/transaction.py`
  - `services/accounting-service/app/models/recurring.py`
  - `services/accounting-service/app/schemas/transaction.py`
  - `services/accounting-service/app/schemas/recurring.py`
  - `services/accounting-service/app/services/transaction_service.py`
  - `services/accounting-service/app/services/recurring_service.py`
  - `services/accounting-service/app/services/analytics_service.py`
  - `services/accounting-service/app/routers/categories.py`
  - `services/accounting-service/alembic/versions/<new>_drop_transaction_category_string.py`
  - `frontend/src/app/models/accounting.model.ts`
  - `frontend/src/app/services/accounting.service.ts`
  - `frontend/src/app/components/accounting/**/*.{ts,html}`（凡讀 `transaction.category` 字串者）
- **API contract (BREAKING)**:
  - `POST /api/accounting/transactions` 不再接受 `category` 字串；缺 `category_id` 回 422。
  - `PUT /api/accounting/transactions/{id}` 同上。
  - `POST /api/accounting/recurring/subscriptions`、訂閱 update、`POST /api/accounting/recurring/installments`、分期 update 同上。
  - 響應仍含 `category` 欄位的場合需確認是否要保留 alias / 改名 `category_name`。
- **Data migration**:
  - SQL backfill 在 Alembic upgrade 一次完成。
  - downgrade 保留 best-effort：可重新加回 `category` 欄位並從 `categories.name` 回填，但不保留歷史 unsynced 漂移狀態。
- **Risk**:
  - 既有資料若有 `category` 字串對不到任何 `categories.name` 又無 `category_id`：migration 會自動建立同名 Category。
  - 前端若有任何送 `category` 字串但沒帶 `category_id` 的路徑，部署後會 422。需在後端 deploy 之前完成前端 audit + 同步部署。
  - 與 sibling change `tighten-accounting-internals` 互不衝突，但建議 `tighten-accounting-internals` 先 land。
