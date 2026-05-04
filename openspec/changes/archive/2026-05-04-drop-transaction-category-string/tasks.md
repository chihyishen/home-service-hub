## 1. 前置檢查

- [x] 1.1 確認 `categories.name` 是否有 unique constraint；若無，先在本 change migration 開頭補加
- [x] 1.2 在 dev DB 跑 baseline SQL（2026-05-04 dev: 6 筆 `category_id IS NULL`，全部 `category="分期付款"`，無雙 NULL）：
  - [x] 1.2.1 `SELECT COUNT(*) FROM transactions WHERE category_id IS NULL` → 6
  - [x] 1.2.2 `SELECT COUNT(*) FROM transactions WHERE category_id IS NULL AND category IS NULL` → 0
  - [x] 1.2.3 同上對 `subscriptions` → 0
- [x] 1.3 將上述查詢結果與處理策略寫進 PR description（commit message 涵蓋）

## 2. Alembic migration（純 SQL backfill + drop）

- [x] 2.1 新增 revision，例如 `<rev>_drop_transaction_category_string.py`
- [x] 2.2 upgrade()：
  - [x] 2.2.1（如必要）為 `categories.name` 加 unique constraint
  - [x] 2.2.2 SQL backfill 1：`UPDATE transactions SET category_id = c.id FROM categories c WHERE t.category_id IS NULL AND t.category = c.name`
  - [x] 2.2.3 SQL orphan-insert：`INSERT INTO categories (name) SELECT DISTINCT category FROM transactions WHERE category_id IS NULL AND category IS NOT NULL ON CONFLICT (name) DO NOTHING`
  - [x] 2.2.4 SQL backfill 2 重跑（覆蓋剛 insert 的）
  - [x] 2.2.5 同 2.2.2–2.2.4 對 `subscriptions`
  - [x] 2.2.6 安全網：SELECT 確認 `transactions.category_id IS NULL` 與 `subscriptions.category_id IS NULL` 都是 0；不為 0 raise
  - [x] 2.2.7 `ALTER TABLE transactions ALTER COLUMN category_id SET NOT NULL`
  - [x] 2.2.8 `ALTER TABLE subscriptions ALTER COLUMN category_id SET NOT NULL`
  - [x] 2.2.9 `ALTER TABLE transactions DROP COLUMN category`
  - [x] 2.2.10 `ALTER TABLE subscriptions DROP COLUMN category`
- [x] 2.3 downgrade()：
  - [x] 2.3.1 `ADD COLUMN category VARCHAR` 回兩張表
  - [x] 2.3.2 SQL backfill：`UPDATE transactions SET category = c.name FROM categories c WHERE t.category_id = c.id`
  - [x] 2.3.3 同上 subscriptions
  - [x] 2.3.4 註解：downgrade 不還原 NOT NULL 解除（保守）
- [x] 2.4 在空 PostgreSQL DB 跑 `alembic upgrade head` → 確認新 schema 正確（pytest fixture 等價驗證，40 passed）
- [x] 2.5 在已有舊資料的 DB（複製 dev 一份）跑 `alembic upgrade head` → 確認 backfill 與 drop 都成功（dev DB 直接驗：null_cat=0、`\d transactions` 無 category 欄位、`category_id` NOT NULL）

## 3. Models

- [x] 3.1 `app/models/transaction.py` 移除 `category: Mapped[str]` 欄位
- [x] 3.2 `app/models/recurring.py` 移除 `Subscription.category` 欄位
- [x] 3.3 確認 `category_id` 在 model 上是 non-nullable

## 4. Schemas

- [x] 4.1 `app/schemas/transaction.py`：
  - [x] 4.1.1 `TransactionCreate.category_id: int`（必填，移除 Optional）
  - [x] 4.1.2 移除 `TransactionCreate.category`、`TransactionUpdate.category`
  - [x] 4.1.3 `Transaction` 響應補 `category_name: str`，從 `category_info.name` 取
- [x] 4.2 `app/schemas/recurring.py`：
  - [x] 4.2.1 `SubscriptionCreate.category_id: int`（必填）
  - [x] 4.2.2 移除 `SubscriptionCreate.category`
  - [x] 4.2.3 響應補 `category_name`
- [x] 4.3 確認 `Installment` schemas 無 legacy `category` 欄位（若有也移除）

## 5. Services

- [x] 5.1 `transaction_service.create_transaction`：移除 `transaction.category = cat.name` 與 `category` 字串檢查；改成沒帶 `category_id` 直接 422（schema 層擋掉）
- [x] 5.2 `transaction_service.update_transaction`：移除 `update_data["category"] = cat.name`
- [x] 5.3 `recurring_service.create_subscription`：同上
- [x] 5.4 `recurring_service.update_subscription`：同上
- [x] 5.5 `recurring_service.create_installment` / `update_installment`：若有 category 同步路徑也移除
- [x] 5.6 `analytics_service._resolve_category_name`：直接 return `transaction.category_info.name`，沒 fallback
- [x] 5.7 `analytics_service._populate_top_expense_fields` 等地方確認不再讀 `transaction.category` 字串

## 6. Routers

- [x] 6.1 `routers/categories.py`：
  - [x] 6.1.1 移除 `_sync_category_name_references`
  - [x] 6.1.2 `update_category` 拿掉 `name_changed` 同步分支（只動 `categories.name`）
  - [x] 6.1.3 `merge_categories` 移除對 `transactions.category` / `subscriptions.category` 字串的 update SQL
  - [x] 6.1.4 `merge_categories` 保留 `category_id` 重指向 + delete source

## 7. Tests

- [x] 7.1 `tests/integration/test_transactions.py`：
  - [x] 7.1.1 補測試：create transaction 不帶 `category_id` → 422
  - [x] 7.1.2 修現有測試：所有 create transaction payload 確保帶 `category_id`
- [x] 7.2 `tests/integration/test_categories.py`：
  - [x] 7.2.1 修改名測試：改名後讀回交易直接顯示新名稱（透過 `category_info.name`，不需 sync）
  - [x] 7.2.2 修 merge 測試：assert transactions / subscriptions 的 `category_id` 變更，移除對 `category` 字串 column 的 assertion
- [x] 7.3 `tests/integration/test_recurring_api.py`：
  - [x] 7.3.1 修 subscription create payload，補必填 `category_id`
- [x] 7.4 `tests/unit/test_analytics_logic.py`：
  - [x] 7.4.1 修若有 mock `transaction.category` 字串的測試 → 改用 `category_info`

## 8. Frontend

- [x] 8.1 audit `frontend/src/app/`：grep `transaction.category`（字串）使用點，逐一改成 `transaction.category_name`
  - [x] 8.1.1 components/accounting/transaction-list
  - [x] 8.1.2 components/accounting/dashboard
  - [x] 8.1.3 components/accounting/recurring-list
  - [x] 8.1.4 其他出現 `.category` 的 template 與 ts
- [x] 8.2 `frontend/src/app/models/accounting.model.ts`：
  - [x] 8.2.1 `Transaction` interface 移除 `category: string`，新增 `category_name: string`
  - [x] 8.2.2 `TransactionCreate` / `TransactionUpdate` interface：`category_id: number`（必填），移除 `category`
  - [x] 8.2.3 `Subscription` 同上
- [x] 8.3 `frontend/src/app/services/accounting.service.ts`：
  - [x] 8.3.1 確認 createTransaction / updateTransaction 不帶 `category` 字串
  - [x] 8.3.2 createSubscription / updateSubscription 同上
- [x] 8.4 `npm test` 與 `npm run build` 全綠

## 9. 部署順序

- [x] 9.1 後端 + Alembic + 前端的 PR 同步合併部署（home-service-hub 是個人單機部署，dev 即 prod，已直接套用）
- [x] 9.2 部署前在 staging（或 dev）跑一次完整 migration smoke（dev DB 已驗證）
- [x] 9.3 部署後驗證：
  - [x] 9.3.1 `\d transactions` 無 `category` 欄位、`category_id` NOT NULL
  - [x] 9.3.2 `\d subscriptions` 同上
  - [x] 9.3.3 月報、年報、月對月顯示分類正確（GET /transactions/report/2026/{2,4} 200，totalIncome 已扣退款）
  - [ ] 9.3.4 改名 / merge 一次完整流程驗證（之後實際使用時再走一次）

## 10. 文件

- [x] 10.1 `services/accounting-service/README.md` 更新分類欄位說明
- [x] 10.2 `docs/accounting-service-improvements.md` 標註本 change 完成
