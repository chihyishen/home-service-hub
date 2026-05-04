## Context

`improve-accounting-data-integrity` change 已收斂大部分一致性問題（refund 防呆、card cycle 負淨額、N+1、category 改名同步、merge 流程）。第二輪掃描補抓出四個更深層、彼此獨立但都屬於 internal contract / refactor 的問題。

本 change 限定：
- 不引入新 API endpoint。
- 不變更現有 endpoint 的 request / response schema。
- 不動 Alembic migration。
- 不改 tracing body 行為（owner 在這輪明確 defer）。

## Goals / Non-Goals

**Goals:**
- 月報 / 年報 / 月對月的 income、expense、category breakdown 把退款 net 出來，不再把退款當收入。
- 收斂 `_get_refunded_amounts` 與 category / payment_method / card 校驗的重複實作。
- 修正 recurring 生成的月底日期截斷。

**Non-Goals:**
- 不改變 transaction list / detail 的回傳結構，refund 仍是兩筆紀錄。
- 不對 refund 引入新 status / type；schema 仍是 `transaction_type = INCOME` + `related_transaction_id`。
- 不引入新 settings / env flag。
- 不處理 `Transaction.category` 字串與 `category_id` 的雙寫問題（由 sibling change `drop-transaction-category-string` 處理）。

## Decisions

### D1. 退款以「net 回原月份的 EXPENSE」處理，不分流到 INCOME

**選擇**：在 analytics 聚合時，對 `INCOME AND related_transaction_id IS NOT NULL` 的交易：
- 不加進 `total_income`。
- 找到 `related_transaction_id` 對應的原 EXPENSE 交易月份與 category，從 `monthly_expense[month]`、`category_monthly_map[category][month]` 扣回該退款金額。
- 若退款 month 與原 EXPENSE month 不同（跨月退款），仍以**原 EXPENSE 月份**為準扣回，理由是「退款是對該筆消費的修正」。

**為什麼**：
- 不需要新欄位、新 status、新表，向下相容 list / detail。
- 對使用者來說「退款月就應該降低當月支出」直覺，但會造成跨月退款的數字不一致；採「綁回原 EXPENSE 月份」可以讓「該月實際淨支出」穩定，不因退款發生時點變動。

**取捨**：
- 跨月退款時，當下月份的 `total_expense` 看不到「退錢進帳」的資訊。前端若要呈現「本月有 X 元退款」，需要另外算（例如把 `INCOME with related_transaction_id` 在當月做次小計）。本 change 不處理前端呈現，留給後續 UI 任務。

### D2. Refund 抵減的計算只看 `transaction_type=INCOME AND related_transaction_id IS NOT NULL`

**選擇**：不需要看 EXPENSE 是否還存在；如果原 EXPENSE 被刪了，退款記錄就成為孤兒，analytics fallback 為「忽略 net 動作，直接也排除這筆 INCOME」（不灌 income，也不能定位到原月份 / category 去 net）。

**為什麼**：刪除原 EXPENSE 是極少數情境（owner 確認硬刪除是預期行為），不值得為了這個建反向 cascade。落到無法 net 時排除而不是當收入，是較保守的數字。

### D3. Helper 抽到 service 層，不動 HTTPException 文案

**選擇**：新增 `app/services/accounting_validation.py`，函式內直接 `raise HTTPException(...)`，detail 字串和現行訊息逐字一致。

**為什麼**：
- 前端可能有依賴 detail 字串做 i18n 或顯示 fallback；保留字串避免 contract drift。
- 若要進一步抽象成 domain exception，留給之後另一輪改動。

### D4. Refund utils 只搬位置不動行為

**選擇**：新增 `app/services/refund_utils.py`，把 `_get_refunded_amounts` 函式原樣搬過去，公開 export。`transaction_service` 與 `analytics_service` 改 import。

**為什麼**：保留行為等價是這次 dedupe 的全部目的，不順便擴大簽名。

### D5. recurring 改用 `safe_date_replace`

**選擇**：

```python
from .billing_service import safe_date_replace

# subscription
new_pending.date = safe_date_replace(today.year, today.month, sub.day_of_month)

# installment
new_pending.date = safe_date_replace(today.year, today.month, inst.start_date.day)
```

**為什麼**：`safe_date_replace` 已有「該月最後一天」的正確語意。把 `min(day, 28)` 換掉同時收斂 billing 與 recurring 的日期解析來源。

## Risks / Trade-offs

- **[Risk] 月報數字變動**：使用者下次打開月報會發現 income 變小（退款被抵掉）。需要在 commit message / release note 解釋。
- **[Risk] 跨月退款的呈現需求**：使用者若期望退款月看到「本月退款 X 元」可能感覺資訊變少。可後續加 UI 切換。
- **[Trade-off] 不引入 refund domain entity**：對長期設計可能還是需要正式的退款 ledger，但本輪先 net；改動成本低、可逆。
- **[Risk] HTTPException detail 重複實作的小漂移**：把 detail 留在原檔案 vs 抽到 helper 都需要保證字串一致。Tests 必須鎖住現有訊息。

## Migration Plan

無資料庫 migration。Code-only refactor。

部署步驟：
1. 執行 backend tests。
2. 部署單一 service，不需配套前端變更。
3. 觀察月報 / 年報數字是否如預期下調 income。

## Open Questions

- 月報是否需要新增一個 `refund_total` 欄位讓前端顯示「本月退款」？本 change 先不加，留給後續 UI 任務。
