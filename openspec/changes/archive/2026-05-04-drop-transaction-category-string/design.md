## Context

`improve-accounting-data-integrity` change 的 D7「分類維持漸進」明確 defer 了「移除 `Transaction.category` 字串欄位」與「強制 `category_id` 必填」。當時理由是不想破壞前端與舊資料輸入流程。

2026-05-04 review，owner 翻轉決議：「我要免除雙寫風險，這是不該存在的」。理由是雙寫的散落同步點越多，未來改 schema 越脆。本 change 把 dual-write 一刀切成單一 source of truth：`category_id` FK。

## Goals / Non-Goals

**Goals:**
- DB 上只有 `category_id` 一個欄位記錄分類；`transactions.category` 與 `subscriptions.category` 欄位徹底刪掉。
- API 上 create / update transaction / subscription / installment 都用 `category_id` 表達分類。
- 改名 / 合併時不需要任何同步寫入 legacy 字串。
- Migration 在 SQL 層完成 backfill，不在 Python 層 loop。

**Non-Goals:**
- 不重新設計分類層級 / hierarchy。
- 不引入 i18n / 別名。
- 不處理 inventory / shopping-list 服務的分類欄位（不在 accounting service）。

## Decisions

### D1. Migration 走純 SQL，分三步：backfill → not null → drop

**選擇**：在單一 Alembic revision 內完成：

```sql
-- 1. backfill from existing categories
UPDATE transactions t
SET category_id = c.id
FROM categories c
WHERE t.category_id IS NULL
  AND t.category IS NOT NULL
  AND t.category = c.name;

-- 2. create missing categories for orphan strings
INSERT INTO categories (name)
SELECT DISTINCT t.category
FROM transactions t
LEFT JOIN categories c ON c.name = t.category
WHERE t.category_id IS NULL
  AND t.category IS NOT NULL
  AND c.id IS NULL
ON CONFLICT (name) DO NOTHING;

-- 3. retry backfill for the newly inserted categories
UPDATE transactions t
SET category_id = c.id
FROM categories c
WHERE t.category_id IS NULL
  AND t.category IS NOT NULL
  AND t.category = c.name;

-- 4. same for subscriptions
UPDATE subscriptions s
SET category_id = c.id
FROM categories c
WHERE s.category_id IS NULL
  AND s.category IS NOT NULL
  AND s.category = c.name;
-- ... orphan + retry 同上 ...

-- 5. NOT NULL constraints
ALTER TABLE transactions ALTER COLUMN category_id SET NOT NULL;
ALTER TABLE subscriptions ALTER COLUMN category_id SET NOT NULL;

-- 6. drop legacy columns
ALTER TABLE transactions DROP COLUMN category;
ALTER TABLE subscriptions DROP COLUMN category;
```

**為什麼**：
- Backfill 不在 Python 端逐筆處理，避免 N+1 與大表 OOM。
- 用 `INSERT ... ON CONFLICT DO NOTHING` 處理 distinct 字串補建，避免重複 INSERT。
- 三段拆開（backfill → orphan-insert → backfill）邏輯線性、好 review、好回滾。

**取捨**：
- 假設 `categories.name` 上有 unique constraint。需確認 baseline migration 已建立此 unique；若沒有就要先 add。

### D2. Migration 失敗時的安全網

**選擇**：在 backfill 結束後、加 NOT NULL 之前，先 SELECT 檢查是否仍有 `category_id IS NULL`。若有，raise 並 abort，不進到 NOT NULL / DROP COLUMN 步驟，保留可重試空間。

**為什麼**：避免在 migration 中產生資料丟失（DROP COLUMN 後沒救）。

實作上可用 `op.execute("DO $$ ... RAISE EXCEPTION ... $$")` 或 alembic 的 `connection.execute(...).scalar()` 主動檢查。

### D3. API 響應保留 `category_name` 而非 `category`

**選擇**：API 響應不再回 `category: str`，改回 `category_name: str`（值來自 `category_info.name`）。如果響應中已有 `category_info` nested object 也維持不變。

**為什麼**：
- 避免命名繼續暗示「Transaction 自己存 category 字串」。
- 前端類型 audit 時可以靠類型系統定位所有舊用法（找 `transaction.category` 編譯錯）。

**取捨**：
- 前端要改類型與 template binding。可接受，因為這次本來就是 breaking。
- 若有其他外部消費者（目前沒有），需要 release note。

### D4. 響應 schema 不再 nest 完整 `category_info`，只回 id + name

**選擇**：響應只暴露 `category_id: int` 與 `category_name: str`，不 nest `Category` object。

**為什麼**：減少 payload 大小、避免重複資料、讓 schema 簡單。（若現行已 nest，可保留，視實作而定。）

### D5. Merge endpoint 簡化

**選擇**：`merge_categories` 移除對 `transactions.category` / `subscriptions.category` 字串的 update SQL。只做：
- `UPDATE transactions SET category_id = target_id WHERE category_id = source_id`
- `UPDATE subscriptions SET category_id = target_id WHERE category_id = source_id`
- `DELETE FROM categories WHERE id = source_id`

**為什麼**：legacy 字串已不存在，merge 變成單純的 FK 重指向。

### D6. 改名同步 helper 移除

`categories.py::_sync_category_name_references` 與其呼叫點 (`update_category` 中 `name_changed` 分支) 全部刪除。改名只動 `categories.name`，因為報表都從 relationship 讀。

## Risks / Trade-offs

- **[Risk] Migration 遇到 `categories.name` 沒 unique**：先確認 / 補加 unique，否則 `ON CONFLICT (name)` 會失敗。
- **[Risk] 前端漏改路徑**：deploy 後 422。Mitigation：前端 PR 與後端 PR 同步上線，CI 加 e2e 驗證 create transaction。
- **[Risk] 既有 DB 有 NULL category 又 NULL category_id 的列**：backfill 不會處理，加 NOT NULL 會失敗。Mitigation：D2 安全網 + 在 PR description 列出檢查 SQL。
- **[Trade-off] 響應改名 `category` → `category_name`**：對前端是 breaking。可接受，作為 dual-write 移除的代價。

## Migration Plan

1. 在 dev DB 跑一次 SQL 檢查：
   ```sql
   SELECT COUNT(*) FROM transactions WHERE category_id IS NULL;
   SELECT COUNT(*) FROM subscriptions WHERE category_id IS NULL;
   SELECT category, COUNT(*) FROM transactions WHERE category_id IS NULL GROUP BY category;
   ```
2. 確認 `categories.name` 有 unique constraint；沒有就先補。
3. 部署順序：
   - 後端 + Alembic + 前端**同步部署**（PR 一起合）。
   - 部署前在 staging / 本地跑完 backfill smoke test。
4. 部署後 verify：
   - `\d transactions` / `\d subscriptions` 不再有 `category` 欄位。
   - `category_id` 為 NOT NULL。
   - 月報、年報、月對月分類顯示正確。

## Open Questions

- 是否要把 `category_name` 也加 unique constraint 在 categories？（出於 ON CONFLICT 需要）若 baseline 沒有，本 change 一併處理。
- merge endpoint 既有測試是否需要重寫？（預期需要，移除「同步 legacy 字串」相關 assertion。）
